from __future__ import print_function

import argparse
import calendar
import hashlib
from io import StringIO
import logging
import os
import platform
import tempfile
import time
import shutil
import subprocess
 
import conda.api
import conda.lock
import conda.resolve
import psutil
import yaml

import conda_execute.config


log = logging.getLogger('conda-execute')


def extract_env_spec(handle):
    spec = []
    in_spec = False
    for line in handle:
        if in_spec is True:
            # FIXME: we are pretty fragile with whitespace at this point.
            if line.startswith('#  - '):
                spec.append(line[5:].strip()) 
            elif not line.startswith('# '):
                # We're done with the spec.
                break
                
        elif line.strip() == '# conda execute env:':
            in_spec = True
    return spec


def extract_spec(fh):
    spec = []
    in_spec = False
    shebang = []

    for i, line in enumerate(fh):
        if i == 0:
            shebang = read_shebang(line)
        if in_spec:
            if not line.strip().startswith('#'):
                break
            spec.append(line.strip(' #\n'))
        elif line.strip() == '# conda execute':
            in_spec = True

    spec = yaml.safe_load(StringIO(u'\n'.join(spec))) or {}
    if 'run_with' in spec:
        spec['run_with'] = spec['run_with'].split()

    if shebang:
        base = os.path.basename(shebang[0])
        conda_shebang = (base == 'conda' or
                             (base == 'env' and len(shebang) > 1 and
                              shebang[1] == 'conda'))
        if not conda_shebang:
            spec.setdefault('run_with', shebang)
        else:
            if platform.system() != 'Windows':
                # TODO: Test this.
                spec.setdefault('run_with', 'sh -c')

    return spec 


def read_shebang(line):
    shebang = []
    if line.startswith("#!"):
        shebang = line[2:].strip().split(" ")
        # Drop off the env part. (see also github.com/polysquare/python-parse-shebang)
        if (platform.system() == "Windows" and shebang and
                os.path.basename(shebang[0]) == "env"):
            shebang = shebang[1:]

    return shebang


def execute(path, force_env=False):
    with open(path, 'r') as fh:
        spec = extract_spec(fh)

    env_spec = spec.get('env', [])
    log.info('Using specification: \n{}'.format(yaml.dump(spec)))

    # TODO: Lock to prevent conda-execute removing any environments.
    with conda.lock.Locked(conda_execute.config.env_dir):
        env_prefix = create_env(env_spec, force_env)
        log.info('Prefix: {}'.format(env_prefix))
        # Register the environment for the conda-execute cache. (PID, creation time etc.)
        # We must do this within the scope of the lock to avoid cleanup race conditions.
        register_env_usage(env_prefix)

    return execute_within_env(env_prefix, spec['run_with'] + [path])


def execute_within_env(env_prefix, cmd):
    if platform.system() == 'Windows':
        paths = [os.path.join(env_prefix),
                 os.path.join(env_prefix, 'Scripts'),
                 os.path.join(env_prefix, 'bin')]
    else:
        paths = [os.path.join(env_prefix, 'bin')]

    environ = os.environ.copy()
    # Note os.pathsep != os.path.sep. It caught me out too ;)
    environ["PATH"] = os.pathsep.join(paths) + os.pathsep + os.environ["PATH"]

    try:
        code = subprocess.check_call(cmd, env=environ)
    except subprocess.CalledProcessError as exception:
        code = exception.returncode
        log.warn('{}: {}'.format(type(exception).__name__, exception))
    except Exception as exception:
        # Everything else gets a non-zero return code.
        code = 42
        log.warn('{}: {}'.format(type(exception).__name__, exception))
    finally:
        return code


def create_env(spec, force_recreation=False):
    """
    Create a temporary environment from the given specification.

    To avoid race conditions, ensure that a lock is attached to the env directory.

    """
    spec = tuple(sorted(spec))
    # Use the first 20 hex characters of the sha256 to make the SHA somewhat legible. This could extend
    # in the future if we have sufficient need.
    hash = hashlib.sha256(u'\n'.join(spec).encode('utf-8')).hexdigest()[:20]
    env_locn = os.path.join(conda_execute.config.env_dir, hash)

    if force_recreation and os.path.exists(env_locn):
        with conda.lock.Locked(conda_execute.config.env_dir):
            log.info("Clearing up existing environment at {} for re-creation".format(env_locn))
            shutil.rmtree(env_locn)

    if not os.path.exists(env_locn):
        channels = ['scitools']
        index = conda.api.get_index(channels)
        # Ditto re the quietness.
        r = conda.resolve.Resolve(index)
        full_list_of_packages = sorted(r.solve(spec))

        # Put out a newline. Conda's solve doesn't do it for us. 
        log.info('\n')

        for tar_name in full_list_of_packages:
            pkg_info = index[tar_name]
            dist_name = tar_name[:-len('.tar.bz2')]
            if not conda.install.is_extracted(conda_execute.config.pkg_dir, dist_name):
                if not conda.install.is_fetched(conda_execute.config.pkg_dir, dist_name):
                    log.info('Fetching {}'.format(dist_name))
                    with conda.lock.Locked(conda_execute.config.pkg_dir):
                        conda.fetch.fetch_pkg(pkg_info, conda_execute.config.pkg_dir)
                with conda.lock.Locked(conda_execute.config.pkg_dir):
                    conda.install.extract(conda_execute.config.pkg_dir, dist_name)
            conda.install.link(conda_execute.config.pkg_dir, env_locn, dist_name)

    return env_locn


def register_env_usage(env_prefix):
    """
    Register the usage of this environment (so that other processes could garbage
    collect when we are done).

    """
    ps = psutil.Process()
    info_file = os.path.join(env_prefix, 'conda-meta', 'execution.log')
    with open(info_file, 'a') as fh:
        # Write out the PID and the integer creation time.
        fh.write('{}, {}\n'.format(ps.pid, int(ps.create_time())))


def main():
    parser = argparse.ArgumentParser(description='Execute a script in a temporary conda environment.')
    parser.add_argument('path', nargs='?',
                        help='The script to execute.')
    parser.add_argument('--force-env', '-f', help='Force re-creation of the environment, even if it already exists.', action='store_true')

    quiet_or_verbose = parser.add_mutually_exclusive_group()
    quiet_or_verbose.add_argument('--verbose', '-v', help='Turn on verbose output.', action='store_true')
    quiet_or_verbose.add_argument('--quiet', '-q', help='Prevent any output, other than that of the script being executed.',
                                  action='store_true')
    import sys
    class StdIn(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            # Values could be None, or an empty list.
            if not values:
                setattr(namespace, self.dest, sys.stdin.readlines())
            else:
                values = [line + '\n' for line in values]
                setattr(namespace, self.dest, values)

    parser.add_argument('--script', '-c', nargs='*', action=StdIn,
                        help='The script to execute.')
 
    args = parser.parse_args() 

    log_level = logging.WARN
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR

    # Configure the logging as desired.
    for logger_name, offset in [('conda-execute', 0),
                                ('conda.resolve', 10),
                                ('stdoutlog', 0),
                                ('dotupdate', 10)]:
        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(log_level + offset)
    log.debug('Arguments passed: {}'.format(args))
    exit_actions = []
    try:
        if args.script:
            with tempfile.NamedTemporaryFile(prefix='conda-execute_', delete=False) as fh:
                fh.writelines(args.script)
                path = fh.name
                log.info('Writing temporary code to {}'.format(path))
                # Queue the temporary file up for cleaning.
                exit_actions.append(lambda: os.remove(path))
        elif args.path:
            path = args.path
        else:
            raise ValueError('Either pass the filename to execute, or pipe with -c.')

        exit(execute(path, force_env=args.force_env))
    finally:
        for action in exit_actions:
            action()

if __name__ == '__main__':
    main()
