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

```
$ ./my_script.py
Re-using environment for "my_script.py" in /tmp/conda-execute/envs/4d31ab21
```


Options:

    in shebang   |   call with conda execute

       True                False                 - create env, then run with the specified program, or sh
       False               True                  - create env, then run with the shebang, or the specified program, or sh.
       True                True                  - create env, then run with the specified program, or sh. Not the shebang though.
       False               False                 - this is just a shell script.

