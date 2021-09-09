from flask import Flask, render_template, request
import sys
import ipaddress

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


@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html',
            corpus_title=config.corpus_title,
        )

    name = request.form['name']
    org = request.form['org']
    email = request.form['email']

    if check_email(email):
        mailer.email_corpus_to(name, email)
        mailer.email_admin(name, org, email, True)
        return render_template('urls_sent.html',
            corpus_title=config.corpus_title,
            name=name,
            email=email,
        )

    else:
        mailer.email_admin(name, org, email, False)
        return render_template('admin_pending.html',
            corpus_title=config.corpus_title,
            name=name,
            email=email,
            admin=config.admin,
        )


@app.route("/respond/<approve>", methods=['GET'])
def respond(approve):
    ensure_admin()
    name = request.args['name']
    org = request.args['org']
    email = request.args['email']
    if approve == 'approve':
        mailer.email_corpus_to(name, email)
        mailer.email_admin(name, org, email, True)
        return render_template('urls_sent.html',
            corpus_title=config.corpus_title,
            name=name,
            org=org,
            email=email,
        )
    else:
        mailer.email_rejection_to(name, org, email)
        return render_template('rejection_sent.html',
            corpus_title=config.corpus_title,
            name=name,
            org=org,
            email=email,
        )



if __name__ == "__main__":
    app.run(host='0.0.0.0')
