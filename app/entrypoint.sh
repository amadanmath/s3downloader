#!/bin/bash

gunicorn s3downloader.wsgi --bind 0.0.0.0:8000
