from flask import Flask, render_template, request, redirect, url_for, abort
import sys
import ipaddress
import yaml
import time
from types import SimpleNamespace

from .config import configure
from .whitelist import check_email
from .mail import Mailer



app = Flask(__name__)
config = configure(app)
mailer = Mailer(app, config)



def ensure_admin():
    ip = ipaddress.ip_address(request.remote_addr)
    if config.admin_ip and not any(ip in network for network in config.admin_ip):
        abort(403)


def load_corpus_data(corpus_id):
    try:
        text = (config.data_dir / f"{corpus_id}.yaml").read_text()
    except FileNotFoundError:
        if (config.data_dir / f"{corpus_id}.lst").is_file():
            text = ''
        else:
            abort(404)

    parsed = yaml.safe_load(text) or {}
    parsed['id'] = corpus_id
    parsed.setdefault('name', corpus_id)
    return SimpleNamespace(**parsed)




@app.route("/", methods=['GET'])
def index():
    return redirect(url_for('corpus', corpus_id=config.default_corpus))


@app.route("/<corpus_id>", methods=['GET', 'POST'])
def corpus(corpus_id):
    corpus = load_corpus_data(corpus_id)
    if request.method == 'GET':
        return render_template('index.html',
            corpus=corpus,
        )

    name = request.form['name']
    org = request.form['org']
    email = request.form['email']

    if check_email(email):
        mailer.email_corpus_to(corpus, name, email)
        mailer.email_admin(corpus, name, org, email, True)
        return render_template('urls_sent.html',
            corpus=corpus,
            name=name,
            email=email,
        )

    else:
        mailer.email_admin(corpus, name, org, email, False)
        return render_template('admin_pending.html',
            corpus=corpus,
            name=name,
            email=email,
            admin=config.admin,
        )


@app.route("/<corpus_id>/respond", methods=['POST'])
def respond(corpus_id):
    data = request.json
    ensure_admin()
    corpus = load_corpus_data(corpus_id)
    approve = data['approved']
    name = data['name']
    org = data['org']
    email = data['email']
    if approve:
        mailer.email_corpus_to(corpus, name, email)
        mailer.email_admin(corpus, name, org, email, True)
    else:
        mailer.email_rejection_to(corpus, name, org, email)
    data['responded_at'] = int(time.time())
    return data



if __name__ == "__main__":
    app.run(host='0.0.0.0')
