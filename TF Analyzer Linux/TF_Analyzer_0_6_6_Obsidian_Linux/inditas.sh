#!/usr/bin/env bash
set -e
cd -- "$(dirname -- "$(readlink -f -- "${BASH_SOURCE[0]}")")"
exec ./start.sh "$@"
