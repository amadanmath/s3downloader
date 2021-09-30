import requests
import os






class WhitelistEntry:
    @classmethod
    def parse(cls, text):
        if text == "<UNI>":
            return UniversityEntry()
        return PatternEntry(text)


class UniversityEntry(WhitelistEntry):
    # https://github.com/Hipo/university-domains-list-api
    _university_checker = 'http://universities.hipolabs.com/search?domain={domain}'
    specificity = 900

    def __call__(self, email):
        try:
            domain = email.split('@')[1]
            r = requests.get(self._university_checker.format(domain=domain))
            result = r.json()
            if result:
                return True
        except Exception:
            logger.exception("Error in university checker")
        return False


class PatternEntry(WhitelistEntry):
    def __init__(self, text):
        self.text = text
        black = text.startswith('!')
        self.white = not black
        if black:
            text = text[1:]
        self.name, at, domain = text.rpartition('@')
        self.domain = domain.split('.')
        self.exact = bool(at)
        self.specificity = 1000 if at else len(self.domain) * 2
        if black:
            self.specificity += 1

    def __call__(self, email):
        name, at, domain = email.rpartition('@')
        domain = domain.split('.')
        if self.exact and self.domain != domain:
            return False
        if self.name and self.name != name:
            return False
        return domain[-len(self.domain):] == self.domain

    def __repr__(self):
        return self.text

    def __eq__(self, other):
        return self.specificity == other.specificity
    def __ne__(self, other):
        return self.specificity == other.specificity
    def __gt__(self, other):
        return self.specificity > other.specificity
    def __lt__(self, other):
        return self.specificity < other.specificity
    def __ge__(self, other):
        return self.specificity >= other.specificity
    def __le__(self, other):
        return self.specificity <= other.specificity


# file format:
#     name@host.domain - exact match of email
#     @host.domain - exact match of host.domain
#     subdomain.domain - match of subdomain.domain or more specific
#     !entry - blacklist instead of whitelist
#     <UNI> - match university list - see UniversityEntry
#     # comments and blank lines are ignored
#     # most specific match is applied
class Whitelist:
    def __init__(self, file):
        self.file = file
        self.whitelist = []
        self.mtime = 0
        self.load()

    def load(self):
        try:
            mtime = os.path.getmtime(self.file)
            if mtime > self.mtime:
                with open(self.file) as r:
                    self.whitelist = []
                    self.mtime = mtime
                    for line in r:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        entry = WhitelistEntry.parse(line)
                        self.whitelist.append(entry)
        except FileNotFoundError:
            self.whitelist = []
            self.mtime = 0

    def __call__(self, email):
        self.load()
        best_match = max((entry for entry in self.whitelist if entry(email)), default=None)
        if not best_match:
            return False
        return best_match.white
