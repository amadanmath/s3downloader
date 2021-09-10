from flask_mail import Mail, Message
from flask import render_template, url_for
import subprocess
import time
import json
from .aws import Presigner



class Mailer():
    def __init__(self, app, config):
        self.mail = Mail(app)
        self.presigner = Presigner(config.aws_profile)
        self.config = config

    def email_corpus_to(self, corpus, name, email):
        corpus_file = (self.config.data_dir / corpus.id).with_suffix('.lst')
        with corpus_file.open('rt', encoding='utf-8') as r:
            urls_list = '\n'.join(self.presigner.presign(file.strip()) for file in r.readlines()) + '\n'

        msg = Message(
            f"Approved: {corpus.name}",
            html=render_template('email.corpus.html',
                corpus=corpus,
            ),
            recipients=[(name, email)],
        )
        msg.attach(f"{corpus.id}.lst", "text/plain", urls_list)
        self.mail.send(msg)


    def email_rejection_to(self, corpus, name, org, email):
        msg = Message(
            f"Not approved: {corpus.name}",
            html=render_template('email.rejection.html',
                corpus=corpus,
                name=name,
                org=org,
                email=email,
            ),
            recipients=[(name, email)],
        )
        self.mail.send(msg)


    def email_admin(self, corpus, name, org, email, approved):
        if approved:
            subject = f"Links to {corpus.name} sent"
            template = "email.notify_admin_notice.html"
            prefix = "sent"
        else:
            print(url_for('respond', approve='approve', corpus_id=corpus.id, name=name, org=org, email=email, _external=True)) # XXX
            subject = f"Links to {corpus.name} requested"
            template = "email.notify_admin_request.html"
            prefix = "requested"

        attachment_name = f"{prefix}-{corpus.id}-{time.time_ns()}.jsonl.enc"
        jsonl = json.dumps({
            "corpus": corpus.id,
            "name": name,
            "org": org,
            "email": email,
            "sent_at": int(time.time()),
            "approved": approved,
        }) + "\n"
        result = subprocess.run(["openssl", "smime", "-encrypt", "-aes-256-cbc", "-outform", "DER", self.config.pubkey_file], input=jsonl.encode('utf-8'), capture_output=True)
        try:
            result.check_returncode()
            json_enc = result.stdout
        except subprocess.CalledProcessError:
            print(result.stderr.decode('utf-8'), file=sys.stderr)
            raise

        msg = Message(
            subject,
            html=render_template(template,
                corpus=corpus,
                prefix=prefix,
                attachment_name=attachment_name,
                name=name,
                org=org,
                email=email,
            ),
            recipients=[self.config.admin],
        )
        msg.attach(attachment_name, "application/octet-stream", json_enc)
        self.mail.send(msg)
