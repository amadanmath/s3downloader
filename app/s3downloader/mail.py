from flask_mail import Mail, Message
from flask import url_for, render_template
import subprocess
import time
import json
import sys



class Mailer():
    def __init__(self, app, config):
        self.mail = Mail(app)
        self.config = config


    def email_corpus_to(self, corpus, name, email):
        signed_list, aria2_list = corpus.signed_urls()
        msg = Message(
            f"Approved: {corpus.name}",
            html=render_template('email.corpus.html',
                corpus=corpus,
            ),
            sender=corpus.sender,
            reply_to=corpus.reply_to,
            recipients=[(name, email)],
        )
        msg.attach(f"{corpus.id}.lst", "text/plain", signed_list)
        msg.attach(f"{corpus.id}.aria2.lst", "text/plain", aria2_list)
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
            sender=corpus.sender,
            reply_to=corpus.reply_to,
            recipients=[(name, email)],
        )
        self.mail.send(msg)


    def email_admin(self, corpus, name, org, email, approved):
        if approved:
            subject = f"Links to {corpus.name} sent"
            template = "email.notify_admin_notice.html"
            prefix = "approved"
            ts_field = "responded_at"
        else:
            subject = f"Links to {corpus.name} requested"
            template = "email.notify_admin_request.html"
            prefix = "requested"
            ts_field = "requested_at"

        attachment_name = f"{prefix}-{corpus.id}-{time.time_ns()}.jsonl.enc"
        data = {
            "corpus": corpus.id,
            "name": name,
            "org": org,
            "email": email,
            ts_field: int(time.time()),
            "response_url": url_for('respond', corpus_id=corpus.id, lang=corpus.lang, _external=True)
        }
        if approved:
            data["approved"] = approved
        jsonl = json.dumps(data) + "\n"
        cmd = ["openssl", "smime", "-encrypt", "-aes-256-cbc", "-outform", "DER", corpus.certificate]
        result = subprocess.run(cmd, input=jsonl.encode('utf-8'), capture_output=True)
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
            ),
            sender=corpus.sender,
            reply_to=corpus.reply_to,
            recipients=[corpus.admin],
        )
        msg.attach(attachment_name, "application/octet-stream", json_enc)
        self.mail.send(msg)
