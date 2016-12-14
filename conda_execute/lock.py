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

        # The implementation of conda's Locked from version 4.2 onward doesn't
        # create parent dir anymore as it did before and, not only that, it
        # now raises an AssertionError if it doesn't exist.
        parent_path = os.path.dirname(path)
        if not os.path.isdir(parent_path):
            os.makedirs(parent_path)

        return conda.lock.Locked.__init__(self, path)
