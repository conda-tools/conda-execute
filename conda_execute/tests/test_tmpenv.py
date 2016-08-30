import logging
import os
import unittest

import conda_execute.execute
import conda_execute.tmpenv

from conda_execute.tests import tmp_script


class Test_tmpenv(unittest.TestCase):
    def test_conda_execute_removes_envs_with_no_exe_log(self):        
        script = """
        # conda execute
        # env:
        #  - python >=3
        #  - numpy
        # run_with: python
        """
        with tmp_script(script) as fname:
            fh = open(fname, 'r')
            spec = conda_execute.execute.extract_spec(fh)
            env_spec = spec.get('env', [])
            env_locn = conda_execute.tmpenv.create_env(env_spec)
            # Remove the execution.log file in this environment to test that 
            # cleanup_tmp_envs removes the environment when it's called
            exe_log_loc = os.path.join(env_locn, 'conda-meta', 'execution.log')
            if os.path.exists(exe_log_loc):
                os.remove(exe_log_loc)
            conda_execute.tmpenv.cleanup_tmp_envs()


if __name__ == '__main__':
    unittest.main()
