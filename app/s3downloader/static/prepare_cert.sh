#!/bin/bash

# Certificate preparation script for S3 downloader
# Usage: ./prepare_cert.sh <email> [private_key] [output_cert]

set -e

EMAIL="$1"
PRIVATE_KEY="${2:-$HOME/.ssh/id_rsa}"
OUTPUT_CERT="${3:-${DATA_DIR:-.}/$EMAIL.crt}"

if [[ -z "$EMAIL" ]]; then
    echo "Usage: $0 <email> [private_key] [output_cert]" >&2
    echo "Example: $0 admin@example.com" >&2
    exit 1
fi

if [[ ! -f "$PRIVATE_KEY" ]]; then
    echo "Error: Private key not found at $PRIVATE_KEY" >&2
    echo "Creating new private key..." >&2
    openssl genrsa -out "${EMAIL}.key" 2048
    PRIVATE_KEY="${EMAIL}.key"
fi

echo "Creating certificate for $EMAIL using private key $PRIVATE_KEY"

# Check if private key is encrypted
if openssl rsa -in "$PRIVATE_KEY" -passin pass: -noout 2>/dev/null; then
    # Unencrypted key - use directly
    PASSIN_ARGS=()
else
    # Encrypted key - prompt for password
    echo -n "Enter pass phrase for $PRIVATE_KEY: "
    read -s PASSWORD
    echo
    export PASSWORD
    PASSIN_ARGS=("-passin" "env:PASSWORD")
fi

# Create certificate signing request
openssl req -new -key "$PRIVATE_KEY" -out "${EMAIL}.csr" \
    -subj "/CN=$EMAIL/emailAddress=$EMAIL/C=JP" "${PASSIN_ARGS[@]}"

# Self-sign the certificate (valid for 1 year)
openssl x509 -req -in "${EMAIL}.csr" -signkey "$PRIVATE_KEY" \
    -out "$OUTPUT_CERT" -days 365 "${PASSIN_ARGS[@]}"

# Clean up CSR
rm -f "${EMAIL}.csr"

echo "Certificate created: $OUTPUT_CERT"
echo "Ask the S3 downloader administrator to place this file in the data directory."
