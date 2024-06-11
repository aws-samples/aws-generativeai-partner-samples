import requests
import boto3
import markdown_to_json
from utils import logger

session = boto3.Session()
aws_region = 'us-west-2'
ec2_client = session.client(service_name='ec2',region_name=aws_region)

class GetECSAmisReleases:
    def execute(self,ami_ids):
        return self.get_ecs_amis_releases_info(ami_ids)

    def get_ecs_amis_releases_info(self, ami_ids):
        response = requests.get("https://api.github.com/repos/aws/amazon-ecs-ami/releases")
        response_json = response.json()
        releases_info = []
        ami_data = []
        for ami_id in ami_ids:
            ami_data.append({
                "name":self.get_ami_name_from_id(ami_id),
                "id": ami_id
            })
        
        for ami in ami_data:
            found_release=False
            for release in response_json:
                details = markdown_to_json.dictify(release['body'])
                for os_name in details.keys():
                    if os_name.startswith('Amazon'):
                        if os_name == "Amazon ECS-optimized Amazon Linux AMI":
                            if ami['name'] in details[os_name]:
                                logger.info(f"Found release notes for {ami['id']}: {ami['name']}")
                                found_release=True
                                releases_info.append({"ami_id": ami['id'], 
                                                        "ami_name":ami['name'],
                                                        "os_name": os_name,
                                                        "details":details[os_name]})
                                break
                        else:
                            for os_architecture in details[os_name].keys():
                                if ami['name'] in details[os_name][os_architecture][0]:
                                    logger.info(f"Found release notes for {ami['id']}: {ami['name']}")
                                    found_release=True
                                    releases_info.append({"ami_id": ami['id'], 
                                                        "ami_name":ami['name'] ,
                                                        "os_architecture": os_architecture,
                                                        "os_name": os_name,
                                                        "details":details[os_name][os_architecture]})
                                    break
            if not found_release:
                raise Exception(f"No release notes were found for {ami['id']}: {ami['name']}")
        return releases_info

    def get_ami_name_from_id(self, ami_id):
        describe_image_response = ec2_client.describe_images(ImageIds=[ami_id])
        return describe_image_response['Images'][0]['Name']
