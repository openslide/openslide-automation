#!/bin/bash

RETENTION=90  # days

set -e

if [ ! -e "$1/buildbot.tac" ] ; then
    echo "Usage: $0 <buildbot-dir>"
    exit 1
fi

# Delete old master logs
find "$1" -maxdepth 1 \
        -name "twistd.log*" -mtime +$RETENTION -delete

# Delete old build logs
find "$1" \
        -name public_html -prune -o \
        -name templates -prune -o \
        -type f -regex "${1%/}/.*/[0-9].*" -mtime +$RETENTION -exec rm {} \;

# Delete old build results
find "${1%/}/public_html/results" -mindepth 1 \
        -mtime +$RETENTION -delete -o \
        -type d -empty -delete

# winbuild snapshots are pruned by winbuild-index.py
