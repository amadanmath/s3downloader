from flask import Flask, render_template, request, url_for
from flask_mail import Mail, Message
import boto3
import requests
import os
import json
import time
from ast import literal_eval
from pathlib import Path
import subprocess
import sys



app = Flask(__name__)



def boolify(s):
    return bool(literal_eval(s))

def listify(s):
    if not s:
        return []
    return s.split(' ')

def parse_email(s):
    match = re.match(r'^(.+?)\s*<(\S+)>$', s)
    return (match[1], match[2])

def emailify(s):
    if not s:
        return []
    return [parse_email(e) for e in re.split(r',\s*', s)]

no_default=object()
def set_from_env(var, default=no_default, kind=None):
    if default == no_default:
        val = os.environ[var]
    else:
        val = os.environ.get(var, no_default)
    if val != no_default:
        if kind and val is not None:
            val = kind(val)
        app.config[var] = val

set_from_env('MAIL_SERVER')
set_from_env('MAIL_PORT', 25, int)
set_from_env('MAIL_USERNAME')
set_from_env('MAIL_PASSWORD')
set_from_env('MAIL_USE_TLS', False, boolify)
set_from_env('MAIL_USE_SSL', False, boolify)
set_from_env('MAIL_DEFAULT_SENDER')
admin = os.environ['MAIL_ADMIN']
corpus_name = os.environ['CORPUS_NAME']
corpus_title = os.environ['CORPUS_TITLE']
aws_profile = os.environ['AWS_PROFILE']
data_dir = Path(os.environ['DATA_DIR'])
pubkey_file = data_dir / "admin.crt"



mail = Mail(app)



seven_days = 8 * 24 * 3600
aws_session = boto3.Session(profile_name=aws_profile)
aws_s3 = aws_session.client('s3')

def presign(path, duration=seven_days):
    bucket, key = path.split('/', 1)
    url = aws_s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': bucket,
            'Key': key,
        },
        ExpiresIn=seven_days,
    )
    return url



# https://github.com/Hipo/university-domains-list-api
university_checker = 'http://universities.hipolabs.com/search?domain={domain}'

def email_is_whitelisted(email):
    try:
        domain = email.split('@')[1]
        r = requests.get(university_checker.format(domain=domain))
        result = r.json()
        if result:
            return True
    except Exception:
        logger.exception("Error in university checker")
    return False


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html',
            corpus_title=corpus_title,
        )

    name = request.form['name']
    org = request.form['org']
    email = request.form['email']

    if email_is_whitelisted(email):
        email_corpus_to(name, email)
        email_admin(name, org, email, True)
        return render_template('urls_sent.html',
            corpus_title=corpus_title,
            name=name,
            email=email,
        )

    else:
        email_admin(name, org, email, False)
        return render_template('admin_pending.html',
            corpus_title=corpus_title,
            name=name,
            email=email,
            admin=admin,
        )


@app.route("/respond/<approve>", methods=['GET'])
def respond(approve):
    name = request.args['name']
    org = request.args['org']
    email = request.args['email']
    if approve == 'approve':
        email_corpus_to(name, email)
        email_admin(name, org, email, True)
        return render_template('urls_sent.html',
            corpus_title=corpus_title,
            name=name,
            org=org,
            email=email,
        )
    else:
        email_rejection_to(name, org, email)
        return render_template('rejection_sent.html',
            corpus_title=corpus_title,
            name=name,
            org=org,
            email=email,
        )




def email_corpus_to(name, email):
    corpus_file = (data_dir / corpus_name).with_suffix('.lst')
    with corpus_file.open('rt', encoding='utf-8') as r:
        urls_list = '\n'.join(presign(file.strip()) for file in r.readlines()) + '\n'

    msg = Message(
        f"Approved: {corpus_title}",
        html=render_template('email.corpus.html',
            corpus_name=corpus_name,
            corpus_title=corpus_title,
        ),
        recipients=[(name, email)],
    )
    msg.attach(f"{corpus_name}.lst", "text/plain", urls_list)
    mail.send(msg)


def email_rejection_to(name, org, email):
    msg = Message(
        f"Not approved: {corpus_title}",
        html=render_template('email.rejection.html',
            name=name,
            org=org,
            email=email,
            corpus_name=corpus_name,
            corpus_title=corpus_title,
        ),
        recipients=[(name, email)],
    )
    mail.send(msg)


def email_admin(name, org, email, approved):
    if approved:
        subject = f"Links to {corpus_title} sent"
        template = "email.notify_admin_notice.html"
        prefix = "sent"
    else:
        print(url_for('respond', approve='approve', name=name, org=org, email=email, _external=True)) # XXX
        subject = f"Links to {corpus_title} requested"
        template = "email.notify_admin_request.html"
        prefix = "requested"

    attachment_name = f"{prefix}-{corpus_name}-{time.time_ns()}.jsonl.enc"
    jsonl = json.dumps({
        "name": name,
        "org": org,
        "email": email,
        "corpus": corpus_name,
        "sent_at": int(time.time()),
        "approved": approved,
    }) + "\n"
    result = subprocess.run(["openssl", "smime", "-encrypt", "-aes-256-cbc", "-outform", "DER", pubkey_file], input=jsonl.encode('utf-8'), capture_output=True)
    try:
        result.check_returncode()
        json_enc = result.stdout
    except subprocess.CalledProcessError:
        print(result.stderr.decode('utf-8'), file=sys.stderr)
        raise

    msg = Message(
        subject,
        html=render_template(template,
            corpus_name=corpus_name,
            corpus_title=corpus_title,
            prefix=prefix,
            attachment_name=attachment_name,
            name=name,
            org=org,
            email=email,
        ),
        recipients=[admin],
    )
    msg.attach(attachment_name, "application/octet-stream", json_enc)
    mail.send(msg)






if __name__ == "__main__":
    app.run(host='0.0.0.0')
