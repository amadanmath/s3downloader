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
