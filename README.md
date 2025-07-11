## Intro

This project is designed to offer S3-hosted datasets

At setup, prepare a signed encryption certificate.
By default, `$HOME/.ssh/id_rsa` will be used as the private key, and
the signed certificate will be placed into `$DATA_DIR/$EMAIL.crt`.

```bash
app/s3downloader/static/prepare_cert.sh <email> [private_key [output_cert]]
```

## Corpus definitions

Place the list of S3 files in `"$DATA_DIR/$CORPUS_ID.lst"` (`bucket/path/to/file`,
one per line).
Add extra data in `"$DATA_DIR/$CORPUS_ID.yaml"`. Example:

```yaml
---
name: corpus name
lang: ja
description: |
  <p>
    HTML description for webpage
  </p>
email: |
  <p
    HTML for email
  </p>
admin: "Who To Ask For Approval <admin@example.com>"
admin_lang: en
admin_ip: "192.168.1.100/32 10.0.0.0/8"  # Optional: IP networks authorized for this corpus
sender: "App's Identity <corpus@example.com>"
reply_to: "Who To Send To When You Reply To Email <admin@example.com>"
```

The `description` field is obligatory, everything else is optional. If `lang`
is not defined, it will default to `en`. If not specified, `email` will
default to `description` — but note that some things are not typically
supported by email clients, like `<style>` or `<video>` tags.

The `admin_ip` field allows you to specify which IP addresses or networks are authorized to approve/reject requests for this specific corpus. This overrides the global `ADMIN_IP` environment variable for this corpus. You can specify multiple networks separated by spaces. If not specified, the global `ADMIN_IP` setting is used.

## Cron Jobs

### URL Pre-signing
`poetry run sign` can be used to pre-pre-sign all the corpora, so that URLs are
not generated when the user requests them. It should be run daily and also when an URL list is added or changed.

```bash
# Add to crontab (crontab -e)
# Run daily at 2 AM
0 2 * * * cd /path/to/s3downloader && poetry run sign
```

### Certificate Expiration Monitoring
Admin certificates expire and need to be renewed. Set up a weekly cron job to check for expiring certificates:

```bash
# Run every Sunday at 8 AM  
0 8 * * 0 cd /path/to/s3downloader && poetry run check-certs
```

This will email admins when their certificates are expiring within 30 days (configurable via `CERT_WARNING_DAYS` environment variable).


## I18n

If you wish to support multiple languages, put `langs` array into the YAML,
and do not define `lang`. The default language will be the first one listed.
Example:

```yaml
---
langs:
  - ja
  - en
```

The app will then expect additional YAML files like `"$CORPUS_ID.ja.yaml"`,
`"$CORPUS_ID.en.yaml"`. Any values in these YAML files will override the
values in the main YAML file.


## Email whitelist

An email whitelist can be set up at `"$DATA_DIR/mail_whitelist.txt"`. If an
email is whitelisted, the admin will not be asked for verification, and the
links will be sent automatically upon request. An email can also be greylisted
in the same file by prepending an exclamation mark. Patterns are listed one
per line. Empty lines and lines starting with `#` are ignored. If an email
matches both a whitelist pattern and a greylist pattern, the more specific one
is applied, with preference to greylist ones in case of a tie. These are the
possible patterns:

```
# a specific email address (only matches user@example.com)
user@example.com

# a specific domain (does not match user@foo.example.com)
@example.com

# a domain with subdomains (does match user@foo.example.com)
example.com
```

There is also a special pattern `<UNI>`, which will whitelist an email address
if it belongs to a known university (per
[university-domains-list-api](https://github.com/Hipo/university-domains-list-api)).

