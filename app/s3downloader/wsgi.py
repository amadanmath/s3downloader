from flask import Flask, render_template, request, redirect, url_for, abort, g
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import ipaddress
import time
from types import SimpleNamespace

from .config import configure
from .corpus import Corpus
from .whitelist import Whitelist
from .util import render
from .mail import Mailer


app = Flask(__name__)
config = configure(app)
if config.num_proxies:
    app.wsgi_app = ProxyFix(app.wsgi_app, **config.num_proxies)
mailer = Mailer(app, config)
whitelist = Whitelist(config.data_dir / 'mail_whitelist.txt')



def ensure_admin():
    ip = ipaddress.ip_address(request.remote_addr)
    if config.admin_ip and not any(ip in network for network in config.admin_ip):
        abort(403)


def get_corpus(corpus_id, lang):
    try:
        corpus = Corpus(corpus_id, lang, config)
    except FileNotFoundError:
        abort(404)

    g.langs = [
        {
            "id": lang,
            "url": request.url_rule.build({**request.view_args, "lang": lang})[1],
        } for lang in corpus.langs
    ]
    return corpus




@app.route("/", methods=['GET'])
def index():
    return redirect(url_for('corpus', corpus_id=config.default_corpus), 307)


@app.route("/<lang>/<corpus_id>", methods=['GET', 'POST'])
@app.route("/<corpus_id>", methods=['GET', 'POST'])
def corpus(corpus_id, lang=None):
    corpus = get_corpus(corpus_id, lang)
    if request.method == 'GET':
        return render('index.html', corpus,
        )

    name = request.form['name']
    org = request.form['org']
    email = request.form['email']

    if whitelist(email):
        mailer.email_corpus_to(corpus, name, email)
        mailer.email_admin(corpus, name, org, email, True)
        return render('urls_sent.html', lang,
            name=name,
            email=email,
        )

    else:
        mailer.email_admin(corpus, name, org, email, False)
        return render('admin_pending.html', corpus,
            name=name,
            email=email,
        )


@app.route("/<lang>/<corpus_id>/respond", methods=['POST'])
@app.route("/<corpus_id>/respond", methods=['POST'])
def respond(corpus_id, lang=None):
    data = request.json
    ensure_admin()
    corpus = get_corpus(corpus_id, lang)

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
