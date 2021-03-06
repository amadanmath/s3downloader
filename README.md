## Intro

This project is designed to offer S3-hosted datasets

At setup, prepare the signed encryption certificate.
By default, `$HOME/.ssh/id_rsa` will be used as the private key, and
the signed certificate will be placed into `$DATA_DIR/$EMAIL.crt`.

```bash
bin/prepare_cert.sh <email> [private_key [output_cert]]
```


## Corpus definitions

Place the list of files in `"$DATA_DIR/$CORPUS_ID.lst"` (`bucket/path/to/file`,
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
sender: "App's Identity <corpus@example.com>"
reply_to: "Who To Send To When You Reply To Email <admin@example.com>"
```

The `description` field is obligatory, everything else is optional. If `lang`
is not defined, it will default to `en`. If not specified, `email` will
default to `description` — but note that some things are not typically
supported by email clients, like `<style>` or `<video>` tags.

`bin/sign.sh` can be used to pre-pre-sign all the corpora, so that URLs are
not generated when the user requests them. It would be best if it was set up
as a daily cron job. It should also be run if an URL list is added or changed.


## I18n

If you wish to support multiple languages, put `langs` array into the YAML,
and do not define `lang`. The default language will be the first one listed.
Example:

```yaml
---
langs:
  - ja
  - en

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

