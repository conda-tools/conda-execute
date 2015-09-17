import logging
import os

import conda.config


log = logging.getLogger('conda-execute')


execute_config = conda.config.rc.get('conda-execute') or {}
env_dir_template = execute_config.get('env-dir', '{config.envs_dirs[0]}/../tmp_envs')

# Expand user and normalize the path.
env_dir = os.path.normpath(os.path.expanduser(env_dir_template.format(config=conda.config)))


pkg_dir_template = execute_config.get('env-dir', '{config.pkgs_dirs[0]}')

# Expand user and normalize the path.
pkg_dir = os.path.normpath(os.path.expanduser(pkg_dir_template.format(config=conda.config)))


