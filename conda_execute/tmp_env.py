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


log = logging.getLogger('conda-tmpenv')


def register_env_usagesss(env_prefix):
    """
    Register the usage of this environment (so that other processes could garbage
    collect when we are done).

    """
    ps = psutil.Process()
    info_file = os.path.join(env_prefix, 'conda-meta', 'execution.log')
    with open(info_file, 'a') as fh:
        fh.write('{}, {}\n'.format(ps.pid, calendar.timegm(time.gmtime())))


def subcommand_list(args):
    """
    The function which handles the list subcommand.

    """
    for env, alive_pids in envs_and_running_pids():
       print('{} users of {}'.format(len(alive_pids), env, ', '.join(map(str, alive_pids))))


def tmp_envs():
    if not os.path.exists(conda_execute.config.env_dir):
        return []
    envs = [os.path.join(conda_execute.config.env_dir, prefix)
            for prefix in os.listdir(conda_execute.config.env_dir)]
    envs = [prefix for prefix in envs
            if os.path.isdir(os.path.join(prefix, 'conda-meta'))]
    return envs

def lock(lock_directory):
    """
    Decorator to get a lock on a directory for the life of the function.

    """
    def locker(fn):
        def new_fn(*args, **kwargs):
            with conda.lock.Locked(lock_directory):
                return fn(*args, **kwargs)
        return new_fn


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
            for pid, creation_time in execution_pids:
                pid = int(pid)
                # Trim off the decimals to simplify comparisson with pid.create_time().
                creation_time = int(float(creation_time))

                # Check if the process is still running.
                alive = (pid in running_pids and
                         int(psutil.Process(pid).create_time()) == creation_time)
                if alive:
                    alive_pids.append(pid)
            yield env, alive_pids


def subcommand_clear(args):
    for env, live_pids in envs_and_running_pids():
        if len(live_pids) == 0:
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
    return args.subcommand_func(args)

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
