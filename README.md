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
admin: "Who To Ask For Approval <admin@example.com>"
sender: "App's Identity <corpus@example.com>"
reply_to: "Who To Send To When You Reply To Email <admin@example.com>"
```

Name is obligatory, everything else is optional.

`bin/sign.sh` can be used to pre-pre-sign all the corpora, so that URLs are
not generated when the user requests them. It would be best if it was set up
as a daily cron job.
