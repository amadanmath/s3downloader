#!/bin/bash

EMAIL="$1"
if [[ -z "$EMAIL" ]]
then
  echo "Usage: $0 <email> [private_key [output_cert]]" > /dev/stderr
  exit 1
fi

PRIVATE_KEY="${2:-"$HOME"/.ssh/id_rsa}"
OUTPUT_CERT="${3:-"${DATA_DIR:-.}"/$EMAIL.crt}"
REQUEST=`mktemp`

echo -n "Enter pass phrase for $PRIVATE_KEY:"
read -s PASSWORD
export PASSWORD

openssl req -new -key "$PRIVATE_KEY" -out "$REQUEST" -subj "/emailAddress=$EMAIL/C=JP" -passin env:PASSWORD
openssl x509 -req -days 372 -in "$REQUEST" -signkey "$PRIVATE_KEY" -out "$OUTPUT_CERT" -passin env:PASSWORD
rm "$REQUEST"
