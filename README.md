At setup, prepare the signed encryption certificate.
By default, `$HOME/.ssh/id_rsa` will be used as the private key, and
the signed certificate will be placed into `$DATA_DIR/admin.crt`.

```
bin/prepare_cert.sh [private_key [output_cert]]
```

Place the list of files in `"$DATA_DIR/$CORPUS_NAME.lst"

Once you have downloaded ".jsonl.enc" files, you can collect them into a
single JSONL file:


```
bin/decrypt.sh [-k private_key] sent-*.jsonl.enc > sent.jsonl
```
