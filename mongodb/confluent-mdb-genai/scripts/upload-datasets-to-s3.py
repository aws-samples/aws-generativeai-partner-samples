import boto3
import os

def upload_folder_to_s3(local_folder, bucket_name, s3_folder=None):
    """
    Uploads a local folder and its contents to an S3 bucket.
    
    :param local_folder: Path to the local folder to upload.
    :param bucket_name: The name of the S3 bucket.
    :param s3_folder: The S3 folder (prefix) to upload to. If None, files are uploaded to the root of the bucket.
    """
    session = boto3.session.Session(profile_name='gameday')
    s3_client = session.client('s3')
    #s3_client = boto3.client('s3')
    
    # Walk through the local folder
    for root, dirs, files in os.walk(local_folder):
        for file in files:
            local_file_path = os.path.join(root, file)
            # Calculate the relative path to create the same structure in S3
            relative_path = os.path.relpath(local_file_path, local_folder)
            s3_file_path = os.path.join(s3_folder, relative_path) if s3_folder else relative_path
            
            # Replace backslashes with forward slashes to ensure correct path in S3
            s3_file_path = s3_file_path.replace("\\", "/")
            
            try:
                s3_client.upload_file(local_file_path, bucket_name, s3_file_path)
                print(f"Uploaded {local_file_path} to s3://{bucket_name}/{s3_file_path}")
            except Exception as e:
                print(f"Failed to upload {local_file_path}: {e}")

# Example usage
local_folder = '../confluent-mongo-aws-power-of-3/data/'  # Replace with your local folder path
bucket_name = 'confluent-mongo-aws-genai'  # Replace with your S3 bucket name
s3_folder = ''  # Replace with your S3 folder (optional), or set to None to upload to the root

upload_folder_to_s3(local_folder, bucket_name, s3_folder)
