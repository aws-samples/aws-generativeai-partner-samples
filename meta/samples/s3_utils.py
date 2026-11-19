# s3_utils.py

import os
import boto3
from botocore.exceptions import ClientError

def upload_file_to_s3(pdf_file, bucket, key, region="us-east-1"):
    """
    Upload a local file to S3. If the bucket doesn't exist, create it.

    Args:
        pdf_file (str): Local file path
        bucket (str): S3 bucket name
        key (str): S3 object key
        region (str): AWS region
    """
    s3 = boto3.client("s3", region_name=region)

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' exists.")
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            print(f"Bucket '{bucket}' not found. Creating it...")
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket)
            else:
                s3.create_bucket(
                    Bucket=bucket,
                    CreateBucketConfiguration={"LocationConstraint": region}
                )
            print(f"Bucket '{bucket}' created.")
        else:
            raise

    # Upload file
    if os.path.exists(pdf_file):
        s3.upload_file(pdf_file, bucket, key)
        print(f"Uploaded {pdf_file} to s3://{bucket}/{key}")
    else:
        raise FileNotFoundError(f"File not found: {pdf_file}")
