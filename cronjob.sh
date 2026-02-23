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
echo "ORG_TOKEN=$(cat $tokenfile)" > .env
code=0
export PYTHONUNBUFFERED=1
time just manage-github --exec || code=$?
echo "Exit: $code"
exit $code
