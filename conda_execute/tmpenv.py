from __future__ import print_function

import argparse
import calendar
import datetime
import hashlib
import logging
import os
import shutil
import time
 
import conda.api
import conda.lock
import conda.resolve
import psutil
import yaml

import conda_execute.config


log = logging.getLogger('conda-tmpenv')


def register_env_usage(env_prefix):
    """
    Register the usage of this environment (so that other processes could garbage
    collect when we are done).

    """
    ps = psutil.Process()
    info_file = os.path.join(env_prefix, 'conda-meta', 'execution.log')
    with open(info_file, 'a') as fh:
        fh.write('{}, {}\n'.format(ps.pid, int(ps.create_time())))


def create_env(spec, force_recreation=False, extra_channels=()):
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
        index = conda.api.get_index(extra_channels)
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


def subcommand_list(args):
    """
    The function which handles the list subcommand.

    """
    for env, env_stats in envs_and_running_pids():
        last_pid_dt = datetime.datetime.fromtimestamp(env_stats['latest_creation_time'])
        age = datetime.datetime.now() - last_pid_dt
        old = age > datetime.timedelta(conda_execute.config.min_age)
        PIDs = env_stats['alive_PIDs']
        if PIDs:
            running_pids = '(running PIDs {})'.format(', '.join(map(str, env_stats['alive_PIDs'])))
        else:
            running_pids = ''
        # TODO Use pretty timedelta printing. e.g. 1 hour 30 mins, or 2 weeks, 6 days and 4 hours etc.
        print('{} processes (newest created {} ago) using {} {}'.format(
                len(PIDs), age, env, running_pids))


def tmp_envs():
    if not os.path.exists(conda_execute.config.env_dir):
        return []
    envs = [os.path.join(conda_execute.config.env_dir, prefix)
            for prefix in os.listdir(conda_execute.config.env_dir)]
    envs = [prefix for prefix in envs
            if os.path.isdir(os.path.join(prefix, 'conda-meta'))]
    return envs


def envs_and_running_pids():
    """
    A lock on temporary environments will be held for the life of the
    generator, so try not to hold on for too long!

    """
    with conda.lock.Locked(conda_execute.config.env_dir):
        running_pids = set(psutil.pids())
        for env in tmp_envs():
            exe_log = os.path.join(env, 'conda-meta', 'execution.log')
            execution_pids = []
            with open(exe_log, 'r') as fh:
                for line in fh:
                    execution_pids.append(line.strip().split(','))
            alive_pids = []
            newest_pid_time = 0
            # Iterate backwards, as we are more likely to hit newer ones first in that order.
            for pid, creation_time in execution_pids[::-1]:
                pid = int(pid)
                # Trim off the decimals to simplify comparisson with pid.create_time().
                creation_time = int(float(creation_time))

                if creation_time > newest_pid_time:
                    newest_pid_time = creation_time

                # Check if the process is still running.
                alive = (pid in running_pids and
                         int(psutil.Process(pid).create_time()) == creation_time)
                if alive:
                    alive_pids.append(pid)
            yield env, {'alive_PIDs': alive_pids, 'latest_creation_time': newest_pid_time}


def subcommand_clear(args):
    return cleanup_tmp_envs(min_age=float(args.min_age))


def cleanup_tmp_envs(min_age=None):
    for env, env_stats in envs_and_running_pids():
        last_pid_dt = datetime.datetime.fromtimestamp(env_stats['latest_creation_time'])
        age = datetime.datetime.now() - last_pid_dt
        if min_age is None:
            min_age = conda_execute.config.min_age
        old = age > datetime.timedelta(min_age)
        if len(env_stats['alive_PIDs']) == 0 and old:
            log.warn('Removing unused temporary environment {}.'.format(env))
            shutil.rmtree(env)


def main():
    parser = argparse.ArgumentParser(description='Manage temporary environments within conda.')
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help')
    common_arguments = argparse.ArgumentParser(add_help=False)
    common_arguments.add_argument('--verbose', '-v', action='store_true')

    list_subcommand = subparsers.add_parser('list', parents=[common_arguments])
    list_subcommand.set_defaults(subcommand_func=subcommand_list)

    clear_subcommand = subparsers.add_parser('clear', parents=[common_arguments])
    clear_subcommand.set_defaults(subcommand_func=subcommand_clear)
    clear_subcommand.add_argument('--min-age', help=('The minimum age for the last registered PID on an '
                                                     'environment, before the environment can be considered '
                                                     'for removal.'), default=None, dest='min_age') 
 
    args = parser.parse_args() 

    log_level = logging.WARN
    if args.verbose:
        log_level = logging.DEBUG

    # Configure the logging as desired.
    for logger_name, offset in [('conda-tmpenv', 0)]:
        logger = logging.getLogger(logger_name)
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(log_level + offset)
    log.debug('Arguments passed: {}'.format(args))
    exit(args.subcommand_func(args))


if __name__ == '__main__':
    main()
