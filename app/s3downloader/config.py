from pathlib import Path
from ast import literal_eval
import os
from types import SimpleNamespace



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
        corpus_name = os.environ['CORPUS_NAME'],
        corpus_title = os.environ['CORPUS_TITLE'],
        aws_profile = os.environ['AWS_PROFILE'],
        data_dir = data_dir,
        pubkey_file = data_dir / "admin.crt",
    )

