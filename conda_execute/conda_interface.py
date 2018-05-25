# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda import __version__ as CONDA_VERSION
from os.path import isfile


def parse_conda_version_major_minor(string):
    return string and tuple(int(x) for x in (string.split('.') + [0, 0])[:2]) or (0, 0)


CONDA_VERSION_MAJOR_MINOR = parse_conda_version_major_minor(CONDA_VERSION)
conda_42 = CONDA_VERSION_MAJOR_MINOR >= (4, 2)
conda_43 = CONDA_VERSION_MAJOR_MINOR >= (4, 3)
conda_44 = CONDA_VERSION_MAJOR_MINOR >= (4, 4)
conda_45 = CONDA_VERSION_MAJOR_MINOR >= (4, 5)

from conda.lock import Locked
Locked = Locked

if conda_44:
    from conda.base.context import user_rc_path, sys_rc_path
    from conda.exports import envs_dirs, pkgs_dirs
    from conda.exports import Resolve
    from conda.exports import get_index
    from conda.common.serialize import yaml_dump, yaml_load
elif conda_42:
    from conda.config import user_rc_path, sys_rc_path
    from conda.exports import envs_dirs, pkgs_dirs
    from conda.exports import Resolve
    from conda.exports import get_index
    from conda.common.yaml import yaml_load
else:
    from conda.config import user_rc_path, sys_rc_path
    from conda.config import envs_dirs, pkgs_dirs
    from conda.resolve import Resolve
    from conda.api import get_index
    from conda.utils import yaml_load

user_rc_path, sys_rc_path = user_rc_path, sys_rc_path
    
envs_dirs, pkgs_dirs = envs_dirs, pkgs_dirs
Resolve = Resolve
get_index = get_index
yaml_load = yaml_load


def collect_rc():
    rc = {}
    if isfile(user_rc_path):
        with open(user_rc_path) as fh:
            rc.update(yaml_load(fh.read()))

    if isfile(sys_rc_path):
        with open(sys_rc_path) as fh:
            rc.update(yaml_load(fh.read()))

    return rc

rc = collect_rc()
