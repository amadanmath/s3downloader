from flask import Flask, render_template, request, redirect, url_for, abort
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import ipaddress
import time
from types import SimpleNamespace

from .config import configure
from .corpus import Corpus
from .whitelist import check_email
from .mail import Mailer


app = Flask(__name__)
config = configure(app)
if config.num_proxies:
    app.wsgi_app = ProxyFix(app.wsgi_app, **config.num_proxies)
mailer = Mailer(app, config)



def ensure_admin():
    ip = ipaddress.ip_address(request.remote_addr)
    if config.admin_ip and not any(ip in network for network in config.admin_ip):
        abort(403)




@app.route("/", methods=['GET'])
def index():
    return redirect(url_for('corpus', corpus_id=config.default_corpus), 307)


@app.route("/<corpus_id>", methods=['GET', 'POST'])
def corpus(corpus_id):
    corpus = Corpus(corpus_id, config)
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
        )


@app.route("/<corpus_id>/respond", methods=['POST'])
def respond(corpus_id):
    data = request.json
    ensure_admin()
    corpus = Corpus(corpus_id, config)
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
