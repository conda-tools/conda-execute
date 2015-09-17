from setuptools import setup
import os.path


vn_context = {}
with open(os.path.join('conda_execute', '_version.py'), 'r') as fh:
    exec(fh.read(), vn_context)
version = vn_context.get('__version__', 'dev')


setup(name='conda-execute',
      version=version,
      description='A tool for executing scripts in a consistent environment.',
      author='Phil Elson',
      author_email='pelson.pub@gmail.com',
      url='https://github.com/pelson/conda-execute',
      packages=['conda_execute'],
      entry_points={
          'console_scripts': [
              'conda-execute = conda_execute.cli:main'
          ]
      },
     )

