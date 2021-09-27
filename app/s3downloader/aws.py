import boto3
from atomicwrites import atomic_write
from itertools import takewhile
from os.path import dirname


seven_days = 7 * 24 * 3600

class Presigner:
    def __init__(self, aws_profile):
        aws_session = boto3.Session(profile_name=aws_profile)
        self.aws_s3 = aws_session.client('s3')


    def presign(self, path, duration=seven_days):
        bucket, key = path.split('/', 1)
        url = self.aws_s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': key,
            },
            ExpiresIn=seven_days,
        )
        return url


    def presign_list(self, corpus, duration=seven_days):
        unsigned_list = corpus.corpus_file.read_text(encoding='utf-8').splitlines()
        if not unsigned_list:
            return [], []

        signed_list = [self.presign(file.strip()) for file in unsigned_list]
        signed_text = '\n'.join(signed_list) + '\n'

        # sorted_list = sorted(unsigned_list)
        # first = sorted_list[0].split('/')
        # last = sorted_list[-1].split('/')
        # prefix = '/'.join(s for s, _ in takewhile(lambda pair: pair[0] == pair[1], zip(first, last)))
        # if prefix:
        #     prefix += '/'
        # prefix_len = len(prefix)
        # aria2_text = ''.join(f"{url}\n dir={dirname(url[prefix_len:])}\n" for url in signed_list)
        aria2_text = ''.join(f"{signed}\n dir={dirname(unsigned)}\n" for unsigned, signed in zip(unsigned_list, signed_list))

        with atomic_write(corpus.signed_file, overwrite=True, mode='wt', encoding='utf-8') as signed_io, atomic_write(corpus.aria2_file, overwrite=True, mode='wt', encoding='utf-8') as aria2_io:
            aria2_io.write(aria2_text)
            signed_io.write(signed_text)
        return signed_text, aria2_text




def sign_all_corpora():
    from .config import configure
    from .corpus import Corpus

    config = configure()
    yaml_files = config.data_dir.glob('*.yaml')
    corpora = [Corpus(file.stem, config) for file in yaml_files]
    presigner = Presigner(config.aws_profile)
    for corpus in corpora:
        presigner.presign_list(corpus)


if __name__ == '__main__':
    sign_all_corpora()
