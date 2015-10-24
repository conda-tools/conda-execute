import os

import conda.lock


class Locked(conda.lock.Locked):
    def __init__(self, directory_to_lock):
        """
        Lock the given directory for use, unlike conda.lock.Lock which
        locks the directory passed, meaning you have to come up with another
        name for the directory to lock.

        """
        dirname, basename = os.path.split(directory_to_lock.rstrip(os.pathsep))
        path = os.path.join(dirname, '.conda-lock_' + basename)
        return conda.lock.Locked.__init__(self, path)
