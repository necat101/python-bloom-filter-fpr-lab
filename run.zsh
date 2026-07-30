#!/usr/bin/env zsh
set -euo pipefail
cd "${0:A:h}"
python3 -m bloomfilter.runner "$@"
