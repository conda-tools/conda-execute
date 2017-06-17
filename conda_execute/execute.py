from __future__ import print_function

import argparse
from io import StringIO
import logging
import os
import platform
import tempfile
import shutil
import stat
import subprocess
import re
import requests

import psutil
import yaml

import conda_execute.config
from conda_execute.tmpenv import (cleanup_tmp_envs, register_env_usage,
                                  create_env)


log = logging.getLogger('conda-execute')
log.addHandler(logging.NullHandler())


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
            line_is_comment = re.search('^\ *\#\ *\#', line)
            if line_is_comment:
                continue
            spec.append(line.strip(' #\n'))
        elif line.strip() in ['# conda execute', '# conda execute:']:
            in_spec = True

    spec = yaml.safe_load(StringIO(u'\n'.join(spec))) or {}
    if 'run_with' in spec:
        if not isinstance(spec['run_with'], list):
            spec['run_with'] = spec['run_with'].split()

    if shebang:
        base = os.path.basename(shebang[0])
        conda_shebang = (base == 'conda' or
                             (base == 'env' and len(shebang) > 1 and
                              shebang[1] == 'conda'))
        if not conda_shebang:
            spec.setdefault('run_with', shebang)

    if platform.system() != 'Windows':
        spec.setdefault('run_with', ['/bin/sh', '-c'])

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


def execute(path, force_env=False, arguments=()):
    with open(path, 'r') as fh:
        spec = extract_spec(fh)

    env_spec = spec.get('env', [])
    if not env_spec:
        raise RuntimeError("No environment was found in the '# conda execute' "
                           "specification.")
    log.info('Using specification: \n{}'.format(yaml.dump(spec)))

    env_prefix = create_env(env_spec, force_env, spec.get('channels', []))
    log.info('Prefix: {}'.format(env_prefix))

    return execute_within_env(env_prefix, spec['run_with'] + [path] + list(arguments))


def execute_within_env(env_prefix, cmd):
    register_env_usage(env_prefix)

    if platform.system() == 'Windows':
        import distutils.spawn
        paths = [os.path.join(env_prefix),
                 os.path.join(env_prefix, 'Scripts'),
                 os.path.join(env_prefix, 'bin')]
        full_path = os.pathsep.join(paths) + os.pathsep + os.environ["PATH"]
        cmd[0] = distutils.spawn.find_executable(cmd[0], path=full_path)
    else:
        paths = [os.path.join(env_prefix, 'bin')]
        # Note os.pathsep != os.path.sep. It caught me out too ;)
        full_path = os.pathsep.join(paths) + os.pathsep + os.environ["PATH"]

    environ = os.environ.copy()
    environ["PATH"] = full_path
    environ["PREFIX"] = env_prefix

    # The default is a non-zero return code. Successful processes will set this themselves.
    code = 42
    try:
        log.debug('Running command: {}'.format(cmd))
        code = subprocess.check_call(cmd, env=environ)
    except subprocess.CalledProcessError as exception:
        code = exception.returncode
        log.warn('{}: {}'.format(type(exception).__name__, exception))
    except Exception as exception:
        log.warn('{}: {}'.format(type(exception).__name__, exception))
    finally:
        return code


def _write_code_to_disk(code):
    with tempfile.NamedTemporaryFile(prefix='conda-execute_',
                                     delete=False, mode='w') as fh:
        fh.writelines(code)
        path = fh.name
        log.info('Writing temporary code to {}'.format(path))
        # Make the file executable.
        os.chmod(path, stat.S_IREAD | stat.S_IEXEC)
        return path


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

    parser.add_argument('--code', '-c', nargs='*', action=StdIn,
                        help='The code to execute.')
    parser.add_argument('remaining_args', help='Remaining arguments are passed through to the called script.',
                        nargs=argparse.REMAINDER)
    args = parser.parse_args()

    log_level = logging.WARN
    if args.verbose:
        log_level = logging.DEBUG
    elif args.quiet:
        log_level = logging.ERROR

    # Configure the logging as desired.
    conda_execute.config.setup_logging(log_level)
    log.debug('Arguments passed: {}'.format(args))

    exit_actions = []

    try:
        if args.code:
            path = _write_code_to_disk(args.code)
            # Queue the temporary file up for cleaning.
            exit_actions.append(lambda: os.remove(path))
        elif args.path:
            # check to see if `args.path` is a remote path, download whatever
            # is at that remote location and stash it as args.code.
            if args.path.startswith('http'):
                # download code from the remote path and write it to disk
                code = requests.get(args.path).content.decode()
                path = _write_code_to_disk(code)
                # Queue the temporary file up for cleaning.
                exit_actions.append(lambda: os.remove(path))
            else:
                path = os.path.abspath(args.path)
        else:
            raise ValueError('Either pass the filename to execute, or pipe with -c.')

        exit_actions.append(cleanup_tmp_envs)
        exit(execute(path, force_env=args.force_env, arguments=args.remaining_args))
    finally:
        for action in exit_actions:
            action()


if __name__ == '__main__':
    main()
