from flask import Flask, render_template, request, redirect, url_for, abort, g
from flask_babel import Babel
from werkzeug.middleware.proxy_fix import ProxyFix
import sys
import ipaddress
import time
import json
import base64
import subprocess
import tempfile
from types import SimpleNamespace


from .config import configure
from .corpus import Corpus
from .whitelist import Whitelist
from .mail import Mailer


app = Flask(__name__)
config = configure(app)
if config.num_proxies:
    app.wsgi_app = ProxyFix(app.wsgi_app, **config.num_proxies)
mailer = Mailer(app, config)
babel = Babel(app)
whitelist = Whitelist(config.data_dir / 'mail_whitelist.txt')


def save_server_config():
    """Save server configuration on each request for use by scripts"""
    server_config_file = config.data_dir / 'server.conf'
    
    # Extract application root from request path
    script_name = request.environ.get('SCRIPT_NAME', '')
    
    server_config = {
        'server_name': request.host,
        'scheme': request.scheme,
        'base_url': request.host_url.rstrip('/'),
        'application_root': script_name
    }
    
    with open(server_config_file, 'w') as f:
        json.dump(server_config, f)


@app.before_request
def before_request():
    """Save server config on each request (only if APP_BASE_URL not defined)"""
    if not config.app_base_url:
        save_server_config()



def verify_admin_signature(data):
    """Verify admin signature using the corpus admin's certificate"""
    try:
        # Extract signature components
        signature_b64 = data['admin_signature']
        signature_data = data['signature_data']
        corpus_id = data['corpus']
        
        # Get the corpus to find the admin's certificate
        corpus = Corpus(corpus_id, config)
        cert_path = corpus.certificate
        
        if not cert_path.exists():
            print(f"Certificate not found: {cert_path}")
            return False
        
        # Recreate the signed data
        signature_text = json.dumps(signature_data, sort_keys=True)
        
        # Decode signature
        signature_bytes = base64.b64decode(signature_b64)
        
        # Extract public key from certificate first
        pubkey_result = subprocess.run([
            "openssl", "x509", "-pubkey", "-noout", "-in", str(cert_path)
        ], capture_output=True, text=True)
        
        if pubkey_result.returncode != 0:
            print(f"Failed to extract public key from certificate: {pubkey_result.stderr}")
            return False
        
        # Verify signature using OpenSSL
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as sig_file, \
             tempfile.NamedTemporaryFile(mode='w', delete=False) as pubkey_file:
            
            sig_file.write(signature_bytes)
            sig_file.flush()
            
            pubkey_file.write(pubkey_result.stdout)
            pubkey_file.flush()
            
            cmd = [
                "openssl", "dgst", "-sha256", "-verify", 
                pubkey_file.name, "-signature", sig_file.name
            ]
            
            result = subprocess.run(cmd, input=signature_text.encode('utf-8'), 
                                  capture_output=True)
            
            # Clean up temp files
            import os
            os.unlink(sig_file.name)
            os.unlink(pubkey_file.name)
            
            if result.returncode == 0:
                return True
            else:
                print(f"Signature verification failed: {result.stderr.decode()}")
                return False
                
    except Exception as e:
        print(f"Error verifying signature: {e}")
        return False


def ensure_admin(corpus=None):
    ip = ipaddress.ip_address(request.remote_addr)
    
    # Check IP address first - use corpus-specific admin IPs if available
    admin_ips = corpus.admin_ip if corpus else config.admin_ip
    if admin_ips and not any(ip in network for network in admin_ips):
        abort(403)
    
    # Check cryptographic signature
    data = request.json
    if not data or 'admin_signature' not in data or 'signature_data' not in data:
        print(f"Missing admin signature from {request.remote_addr}")
        abort(403)
    
    if not verify_admin_signature(data):
        print(f"Invalid admin signature from {request.remote_addr}")
        abort(403)


def get_corpus(corpus_id, lang):
    try:
        corpus = Corpus(corpus_id, config, lang)
    except FileNotFoundError:
        abort(404)

    g.lang = corpus.lang
    g.langs = corpus.langs and [
        {
            "id": lang,
            "url": url_for(request.endpoint, **{**request.view_args, "lang": lang}),
        } for lang in corpus.langs
    ]
    return corpus



@babel.localeselector
def get_locale():
    try:
        return g.lang
    except AttributeError:
        return 'en'



@app.route("/", methods=['GET'])
def index():
    return redirect(url_for('corpus', corpus_id=config.default_corpus), 307)


@app.route("/<lang>/<corpus_id>", methods=['GET', 'POST'])
@app.route("/<corpus_id>", methods=['GET', 'POST'])
def corpus(corpus_id, lang=None):
    corpus = get_corpus(corpus_id, lang)
    if request.method == 'GET':
        if corpus.langs and not lang:
            return redirect(url_for('corpus', corpus_id=corpus.id, lang=corpus.lang), code=307)
        return render_template('index.html',
            corpus=corpus,
        )

    name = request.form['name']
    org = request.form['org']
    email = request.form['email']

    if whitelist(email):
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


@app.route("/<lang>/<corpus_id>/respond", methods=['POST'])
def respond(corpus_id, lang=None):
    data = request.json
    corpus = get_corpus(corpus_id, lang)
    ensure_admin(corpus)

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
