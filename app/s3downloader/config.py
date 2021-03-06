from pathlib import Path
from ipaddress import ip_network
from ast import literal_eval
from types import SimpleNamespace
import os
import re



def boolify(s):
    return bool(literal_eval(s))


def email(s, just_email=False):
    match = re.match(r'^(.+?)\s*<(\S+)>$', s)
    if match:
        if just_email:
            return match[2]
        else:
            return (match[1], match[2])
    else:
        return s


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
def configure(app=None):
    if app:
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

    # set_from_env('MAIL_DEFAULT_SENDER')
    data_dir = Path(os.environ['DATA_DIR'])
    default_admin = os.environ['DEFAULT_ADMIN']
    default_sender = os.environ.get('DEFAULT_SENDER', default_admin)
    default_reply_to = os.environ.get('DEFAULT_REPLY_TO', default_sender)

    return SimpleNamespace(
        admin_ip = split(os.environ.get('ADMIN_IP', ''), ip_network),
        default_admin = default_admin,
        default_corpus = os.environ['DEFAULT_CORPUS'],
        default_sender = default_sender,
        default_reply_to = default_reply_to,
        aws_profile = os.environ['AWS_PROFILE'],
        num_proxies = parse_dict(os.environ.get('NUM_PROXIES')),
        data_dir = data_dir,
    )

