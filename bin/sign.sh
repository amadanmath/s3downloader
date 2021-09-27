#!/bin/bash

# crontab
# 0	0	*	*	*	/path/to/s3downloader/bin/sign.sh /path/to/envfile

envpath="$1"
if [[ -z "$envpath" ]]
then
  echo "Usage: $0 <env_file>" > /dev/stderr
  exit 1
fi
source "$envpath"

top="$(cd "$(dirname "$0")"/..; pwd)"
cd "$top/app"
"$top/venv/bin/python" -m s3downloader.aws
