import time
import yaml
from datetime import timedelta
from .aws import Presigner
from .config import email



class Corpus:
    def __init__(self, corpus_id, config):
        self.config = config

        text = (config.data_dir / f"{corpus_id}.yaml").read_text()
        parsed = yaml.safe_load(text) or {}

        self.id = corpus_id
        self.name = parsed.get('name', corpus_id)
        self.description = parsed['description']
        self.email = parsed['email']

        self.admin = parsed.get('admin', config.default_admin)
        self.sender = parsed.get('sender', config.default_sender)
        self.reply_to = parsed.get('reply_to', config.default_reply_to)
        admin_email = email(self.admin, just_email=True)
        self.certificate = config.data_dir / f"{admin_email}.crt"

        self.corpus_file = config.data_dir / f"{corpus_id}.lst"
        self.signed_file = config.data_dir / f"{corpus_id}.signed.lst"


    def signed_urls(self):
        if self.signed_file.is_file():
            age = time.time() - self.signed_file.stat().st_mtime
            if timedelta(seconds=age) < timedelta(days=2):
                return self.signed_file.read_text(encoding='utf-8')
        presigner = Presigner(self.config.aws_profile)
        return presigner.presign_list(self)
