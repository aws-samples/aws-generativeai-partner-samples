
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    RemovalPolicy
)
from constructs import Construct
from config import DsConfig

class S3Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        bucket_name = DsConfig.S3_BUCKET_NAME
        # Create S3 bucket with auto-delete on stack destruction
        self.bucket = s3.Bucket(
            self, 
            "AssetsBucket",
            bucket_name=bucket_name,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )

        # Deploy assets from local directory to S3
        s3deploy.BucketDeployment(
            self,
            "DeployAssets",
            sources=[s3deploy.Source.asset("assets/kb-docs")],
            destination_bucket=self.bucket
        )