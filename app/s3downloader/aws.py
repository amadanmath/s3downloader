import boto3


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
        unsigned_list = corpus.corpus_file.read_text(encoding='utf-8')
        signed_list = '\n'.join(self.presign(file.strip()) for file in unsigned_list.splitlines()) + '\n'
        corpus.signed_file.write_text(signed_list, encoding='utf-8')
        return signed_list




def sign_all_corpora():
    from .config import configure
    from .corpus import Corpus

    config = configure()
    yaml_files = config.data_dir.glob('*.yaml')
    corpora = [Corpus(file.stem, config) for file in yaml_files]
    for corpus in corpora:
        corpus.signed_urls()


if __name__ == '__main__':
    sign_all_corpora()
