#!/bin/bash

PRIVATE_KEY="${1:-"$HOME"/.ssh/id_rsa}"
OUTPUT_CERT="${2:-"${DATA_DIR:-.}"/admin.crt}"
REQUEST=`mktemp`

openssl req -new -key "$PRIVATE_KEY" -out "$REQUEST"
openssl x509 -req -days 372 -in "$REQUEST" -signkey "$PRIVATE_KEY" -out "$OUTPUT_CERT"
rm "$REQUEST"
