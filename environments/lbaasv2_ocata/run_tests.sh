#!/bin/bash 

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

tempest run -t --blacklist-file $DIR/blacklist.txt
testr last --subunit | subunit2junitxml --output-to=tempest.xml

