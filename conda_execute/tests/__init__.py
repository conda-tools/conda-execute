from contextlib import contextmanager
import tempfile
import textwrap


@contextmanager 
def tmp_script(lines, tmpfile_kwargs=None):
    """
    A context manager which takes the multiline string and writes to a temporary file.

    """ 
    tmpfile_kwargs = tmpfile_kwargs or {}
    tmpfile_kwargs.setdefault('mode', 'w')
    tmpfile_kwargs.setdefault('suffix', '.sh')
    with tempfile.NamedTemporaryFile(**tmpfile_kwargs) as fh: 
        fh.write(textwrap.dedent(lines).strip())
        fh.flush() 
        yield fh.name
