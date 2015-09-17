
set -x -e

example_script=$(dirname $0)/../example.sh
tmp_script=$(dirname $0)/executable_script.sh


conda execute -c "# conda execute" "# env:" "# - python" "# run_with: python" "print('hello')" -v

conda execute -v -c <<EOF
# conda execute
# env:
# - python
# run_with: python
print('hello')

EOF

cat $example_script | conda execute -c

conda execute $example_script


cat <<EOF > $tmp_script
#!/usr/bin/env conda execute -v 
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

print(np.random.normal(5, 2, 10))

EOF
chmod u+x $tmp_script
$tmp_script

