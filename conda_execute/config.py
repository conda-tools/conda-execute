import logging
import os

import conda.config


log = logging.getLogger('conda-execute')


def setup_logging(level):
    # Configure the logging as desired.
    for logger_name, offset in [('conda-execute', 0),
                                ('conda-tmpenv', 0),
                                ('conda.resolve', 10),
                                ('stdoutlog', 0),
                                ('dotupdate', 10)]:
        logger = logging.getLogger(logger_name)
        if all([isinstance(handler, logging.NullHandler) for handler in logger.handlers]):
            logger.addHandler(logging.StreamHandler())
        logger.setLevel(level + offset)


execute_config = conda.config.rc.get('conda-execute') or {}
env_dir_template = execute_config.get('env-dir', '{config.envs_dirs[0]}/../tmp_envs')

# Expand user and normalize the path.
env_dir = os.path.normpath(os.path.expanduser(env_dir_template.format(config=conda.config)))


# The miniumum amount of time since a new process has used an environment
# (in hours) before it can be considered for removing.
min_age = execute_config.get('remove-if-unused-for', 25)


pkg_dir_template = execute_config.get('pkg-dir', '{config.pkgs_dirs[0]}')

# Expand user and normalize the path.
pkg_dir = os.path.normpath(os.path.expanduser(pkg_dir_template.format(config=conda.config)))


