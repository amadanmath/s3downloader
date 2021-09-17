This project is designed to offer S3-hosted datasets

At setup, prepare the signed encryption certificate.
By default, `$HOME/.ssh/id_rsa` will be used as the private key, and
the signed certificate will be placed into `$DATA_DIR/admin.crt`.

```bash
bin/prepare_cert.sh [private_key [output_cert]]
```

Place the list of files in `"$DATA_DIR/$CORPUS_ID.lst"` (`bucket/path/to/file`,
one per line).
Add extra data in `"$DATA_DIR/$CORPUS_ID.yaml"`. Example:

```yaml
---
name: corpus name
description: |
  <p>
    html description
  </p>
email: |
  <p>
    additional text for email (e.g. licence?)
  </p>
```

Once you have downloaded `.jsonl.enc` files, you can collect them into a
single JSONL file:


```bash
bin/decrypt.sh [-k private_key] sent-*.jsonl.enc > sent.jsonl
```
