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

    def email_corpus_to(self, name, email):
        corpus_file = (self.config.data_dir / self.config.corpus_name).with_suffix('.lst')
        with corpus_file.open('rt', encoding='utf-8') as r:
            urls_list = '\n'.join(self.presigner.presign(file.strip()) for file in r.readlines()) + '\n'

        msg = Message(
            f"Approved: {self.config.corpus_title}",
            html=render_template('email.corpus.html',
                corpus_name=self.config.corpus_name,
                corpus_title=self.config.corpus_title,
            ),
            recipients=[(name, email)],
        )
        msg.attach(f"{self.config.corpus_name}.lst", "text/plain", urls_list)
        self.mail.send(msg)


    def email_rejection_to(self, name, org, email):
        msg = Message(
            f"Not approved: {self.config.corpus_title}",
            html=render_template('email.rejection.html',
                name=name,
                org=org,
                email=email,
                corpus_name=self.config.corpus_name,
                corpus_title=self.config.corpus_title,
            ),
            recipients=[(name, email)],
        )
        self.mail.send(msg)


    def email_admin(self, name, org, email, approved):
        if approved:
            subject = f"Links to {self.config.corpus_title} sent"
            template = "email.notify_admin_notice.html"
            prefix = "sent"
        else:
            print(url_for('respond', approve='approve', name=name, org=org, email=email, _external=True)) # XXX
            subject = f"Links to {self.config.corpus_title} requested"
            template = "email.notify_admin_request.html"
            prefix = "requested"

        attachment_name = f"{prefix}-{self.config.corpus_name}-{time.time_ns()}.jsonl.enc"
        jsonl = json.dumps({
            "name": name,
            "org": org,
            "email": email,
            "corpus": self.config.corpus_name,
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
                corpus_name=self.config.corpus_name,
                corpus_title=self.config.corpus_title,
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
