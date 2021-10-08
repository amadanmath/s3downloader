import time
import yaml
from flask import render_template_string
from datetime import timedelta
from .aws import Presigner
from .config import email


class Corpus:
    def __init__(self, corpus_id, lang, config):
        parts = corpus_id.rpartition('.')
        if len(parts[2]) == 2 and not lang and parts[0]:
            corpus_id, _, lang = parts

        text = (config.data_dir / f"{corpus_id}.yaml").read_text()
        parsed = yaml.safe_load(text) or {}

        self.langs = parsed.get('langs')
        if self.langs:
            if not lang:
                lang = self.langs[0]
            text = (config.data_dir / f"{corpus_id}.{lang}.yaml").read_text()
            parsed.update(yaml.safe_load(text) or {})
        else:
            lang = parsed.get('lang')
            if not lang:
                lang = 'en'

        self.id = corpus_id
        self.lang = lang
        self.config = config
        self.name = parsed.get('name', corpus_id)
        self.description = parsed['description']
        self.email = parsed.get('email', self.description)

        self.admin = parsed.get('admin', config.default_admin)
        self.admin_lang = parsed.get('admin_lang')
        self.sender = parsed.get('sender', config.default_sender)
        self.reply_to = parsed.get('reply_to', config.default_reply_to)
        admin_email = email(self.admin, just_email=True)
        self.certificate = config.data_dir / f"{admin_email}.crt"

        self.corpus_file = config.data_dir / f"{corpus_id}.lst"
        self.signed_file = config.data_dir / f"{corpus_id}.signed.lst"
        self.aria2_file = config.data_dir / f"{corpus_id}.aria2.lst"


    @property
    def rendered_description(self):
        return render_template_string(self.description, corpus=self)

    @property
    def rendered_email(self):
        return render_template_string(self.email, corpus=self)


    def signed_urls(self):
        if self.signed_file.is_file():
            age = time.time() - self.signed_file.stat().st_mtime
            if timedelta(seconds=age) < timedelta(days=2):
                signed = self.signed_file.read_text(encoding='utf-8')
                aria2 = self.aria2_file.read_text(encoding='utf-8')
                return (signed, aria2)
        presigner = Presigner(self.config.aws_profile)
        return presigner.presign_list(self)
