#!/bin/bash

set -e

envpath="$1"
if [[ -z "$envpath" ]]
then
  echo "Usage: $0 <env_file>" > /dev/stderr
  exit 1
fi
set -a
source "$envpath"
set +a

top="$(cd "$(dirname "$0")"/..; pwd)"
PYTHONPATH="$top/app" "$top/venv/bin/python" -m s3downloader.aws
