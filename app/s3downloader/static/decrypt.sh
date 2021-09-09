#!/bin/bash

if [[ -z "$1" ]]
then
  echo "Usage: $0 [-k private_key] enc_file [enc_file...]" >/dev/stderr
  exit 1
fi

PRIVATE_KEY=$HOME/.ssh/id_rsa
if [[ "$1" == "-k" ]]
then
  PRIVATE_KEY="$2"
  shift 2
fi

set -e
read -s -e -r -p "Enter pass phrase for $PRIVATE_KEY: " passphrase
echo > /dev/stderr
for file in "$@"
do
  openssl smime -decrypt -binary -inform DER -inkey "$PRIVATE_KEY" -in "$file" -passin pass:"$passphrase"
done
