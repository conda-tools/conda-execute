
import os
import tempfile
import unittest
import uuid

from conda_execute.lock import Locked


class Test_Locked(unittest.TestCase):

    def test_locked_parent_dir_always_exists(self):
        temp_dir = tempfile.mkdtemp()
        parent_dir = os.path.join(temp_dir, str(uuid.uuid4()), 'fake-env')
        with Locked(parent_dir) as locked:
            assert os.path.isdir(locked.directory_path)


if __name__ == '__main__':
    unittest.main()
