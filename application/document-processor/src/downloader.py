import boto3
from config import AWS_REGION

s3 = boto3.client("s3", region_name=AWS_REGION)

def download_object(bucket: str, key: str) -> bytes:
    response = s3.get_object(Bucket=bucket, Key=key)
    return response["Body"].read()
