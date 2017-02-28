conda execute
-------------

A tool for executing scripts in a defined temporary environment.

```python
$ cat my_script.py 
#!/usr/bin/env python
"""
A script that uses numpy's random normal distribution to print 3 numbers.

"""

# conda execute
# env:
#  - python >=3
#  - numpy

import numpy as np

print(np.random.normal(size=3))
```

```
$ conda execute -v my_script.py 
Using specification: 
env: [python >=3, numpy]
run_with: [/usr/bin/env, python]

Prefix: /Users/pelson/miniconda/tmp_envs/ea977067a8fbeb21a594

[ 1.06976755  1.23957678  0.09308639]
```

Installing ``conda execute``
----------------------------

Conda execute is installable into the root conda environment with:

```
conda install conda-execute --channel=conda-forge
```

Alternatively, conda-execute is a pure-python package, and is easy to install from source.


Running a conda execute script from the command line without the ``conda execute`` prefix
-----------------------------------------------------------------------------------------
If you want to make a shell script that can be run with conda execute directly, rather than having to call ``conda execute`` each time,
ensure that the shebang points at ``conda-execute`` and the ``run_with`` metadata is defined:

```python
$ cat execute_directly.py 
#!/usr/bin/env conda-execute
"""
A script that uses numpy's random normal distribution to print 3 numbers.

"""

# conda execute
# env:
#  - python >=3
#  - numpy
# run_with: python

import numpy as np

print(np.random.normal(size=3))

```

```
$ ./execute_directly.py 
[-0.46194591  0.13287211 -0.10139428]
```

``conda tmpenv`` and cleaning up
--------------------------------

conda execute automatically cleans up all environments which are unused in the last N hours (configurable, default 25).
However, to manually run the cleanup process, it is possible to inspect the temporary environments with:

```$ conda tmpenv list```

And any environments with 0 running processes can be removed with:

```$ conda tmpenv clear```


Process safety
--------------

conda execute has been written to allow concurrent conda execute usage whilst at the same time sharing environments.
This means that conda execute must make use of conda's locking machinery to avoid race-conditions.
If you experience issues with the locking, please raise an issue with as much detail as possible.
