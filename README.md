conda execute
-------------

A tool for executing scripts in a defined temporary environment.

```
$ cat my_script.py
#!/usr/bin/env python
"""
A script that uses numpy's random normal distribution to print 10 numbers.

"""

# conda execute
# env:
#  - python >=3
#  - numpy

# We import numpy, and print... that's it.
import numpy as np

print(numpy.random.normal(5, 2, 10))

```

```
$ conda execute my_script.py
Creating environment for "my_script.py" in /tmp/conda-execute/envs/4d31ab21
```

Alternatively, if you want to make a shell script that can be executed directly:

```
$ cat my_script.py
#!/use/bin/env conda execute
"""
A script that uses numpy's random normal distribution to print 10 numbers.

"""

# conda execute
# env:
#  - python >=3
#  - numpy
# run_with: python

# We import numpy, and print... that's it.
import numpy as np

print(numpy.random.normal(5, 2, 10))

```

Cleaning up
-----------

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
