#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
python $DIR/clean_bigip.py --config-file=$DIR/../etc/f5-agent.conf

