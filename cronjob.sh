#!/bin/bash
set -euo pipefail
date
tokenfile=/home/wavy/datalab/opensafely-sysadmin/org-token
checkout=/tmp/opensafely-sysadmin
if test -d $checkout; then
    git -C $checkout pull
else
    git clone https://github.com/opensafely-core/sysadmin.git $checkout
fi

cd $checkout
code=0
export PYTHONUNBUFFERED=1
time make manage ARGS=--exec ORG_TOKEN="$(<$tokenfile)" || code=$?
echo "Exit: $code"
exit $code
