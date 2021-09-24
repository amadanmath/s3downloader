#!/bin/bash

here="$(dirname "$0")"
source "$here/../venv/bin/activate"
cd "$here/../app"
python -m s3downloader.aws
