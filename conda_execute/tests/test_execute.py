import unittest

from conda_execute.tests import tmp_script
from conda_execute import execute


class Test_execute(unittest.TestCase):
    def test_no_env_specified(self):
        script = """
        # conda execute
        """
        msg = 'No environment was found in the .* specification'
        with tmp_script(script) as fname:
            with self.assertRaisesRegexp(RuntimeError, msg):
                execute.execute(fname)


class Test_extract_spec(unittest.TestCase):
    def get_spec(self, script):
        with tmp_script(script) as fname:
            with open(fname, 'r') as fh:
                return execute.extract_spec(fh)

    def test_no_spec(self):
        script = "echo 'hello'"
        spec = self.get_spec(script)
        # Only true on non-Windows.
        self.assertEqual(spec, {'run_with': ['/bin/sh', '-c']})

    def test_run_with_split(self):
        script = """
        # conda execute
        # run_with: hello world
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['hello', 'world']})

    def test_run_with_split_override(self):
        script = """
        # conda execute
        # run_with: ["hello world"]
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['hello world']})

    def test_run_with_from_shebang(self):
        script = """
        #!/usr/bin/env python
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['/usr/bin/env', 'python']})

    def test_run_with_from_shebang_conda(self):
        script = """
        #!/usr/bin/env conda
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['/bin/sh', '-c']})

    def test_run_with_from_shebang_conda2(self):
        script = """
        #!/path/to/bin/conda
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['/bin/sh', '-c']})

    def test_run_with_not_from_shebang(self):
        script = """
        #!/path/to/bin/conda
        # conda execute
        #  run_with: python
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['python']})

    def test_fluffy_conda_execute_header(self):
        # The colon technically isn't necessary, but we support it.
        script = """
        # conda execute:
        #  run_with: wibble
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['wibble']})

    def test_comment(self):
        script = """
        # conda execute
        #   # This is a comment
        # # This is another comment
         ## This is a final comment
        #  run_with: python
        """
        spec = self.get_spec(script)
        self.assertEqual(spec, {'run_with': ['python']})

if __name__ == '__main__':
    unittest.main()
