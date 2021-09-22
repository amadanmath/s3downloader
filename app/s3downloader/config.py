from pathlib import Path
from ipaddress import ip_network
from ast import literal_eval
from types import SimpleNamespace
import os
import re



def boolify(s):
    return bool(literal_eval(s))


def email(s):
    match = re.match(r'^(.+?)\s*<(\S+)>$', s)
    return (match[1], match[2])


def split(s, kind=str, sep=r'[\s,]\s*'):
    if not s:
        return []
    return [kind(e) for e in re.split(sep, s)]


def parse_dict(s):
    result = {}
    for part in split(s):
        k, v = part.split('=', 1)
        result[k] = int(v)
    return result



_no_default=object()
def configure(app):
    def set_from_env(var, default=_no_default, kind=None):
        if default == _no_default:
            val = os.environ[var]
        else:
            val = os.environ.get(var, _no_default)
        if val != _no_default:
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
    data_dir = Path(os.environ['DATA_DIR'])

    return SimpleNamespace(
        admin = os.environ['MAIL_ADMIN'],
        admin_ip = split(os.environ.get('ADMIN_IP', ''), ip_network),
        default_corpus = os.environ['DEFAULT_CORPUS'],
        aws_profile = os.environ['AWS_PROFILE'],
        num_proxies = parse_dict(os.environ.get('NUM_PROXIES')),
        data_dir = data_dir,
        pubkey_file = data_dir / "admin.crt",
    )

