#!/bin/bash

PWD="$(pwd)"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR
for d in */ ; do
    /bin/bash -c ${d}install.sh
done
cd $PWD

