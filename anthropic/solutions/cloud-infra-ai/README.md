# Cloud Infra AI

Application that integrates with terraform plans to provide additional information of changes that are related to Elastic Container Service AMIs with tool use, Amazon Bedrock and Anthropic Claude 3 Sonnet

## Prerequisites

* Python3
* An AWS account with access to Claude3 sonnet
* Terraform


## Installation

1. Clone this repo and navigate to the cloud-infra-ai folder
```
git clone https://github.com/aws-samples/aws-generativeai-partner-samples.git
cd aws-generativeai-partner-samples/anthropic/solutions/cloud-infra-ai
```

2. Install requirements

Optional - Create a virtual environment
```
python3 -m virtualenv .env
source .env/bin/activate
```

Install requirements
```
pip install -r requirements.txt
```

Test with '--help' option
```
python main.py --help
```

Example output
```
Usage: main.py [OPTIONS] COMMAND [ARGS]...

Options:
  --verbose  Print detailed information in output besides the final report
  --help     Show this message and exit.

Commands:
  eval
```

## Usage example

1. The application requires a terraform project to be tested. This repo includes one in the terraform folder

```
cd ./terraform
terraform apply --auto-approve
```

2. Once applied, modify the ECS AMI with the following command - this will be detected by the app.

```
sed -i -e 's/ecs_optimized_ami_linux_2.value/ecs_optimized_ami_linux_2023.value/g' main.tf
```

3. Run the application - the AMI details fetched using tool use with Claude 3 should be in the output

_Note: Make sure to navigate to the aws-generativeai-partner-samples/solutions/cloud-infra-ai before executing the following command_

```
# Assuming current directory is "./terraform"
cd .. 
python main.py eval --project-directory ./terraform
```

Example output
```
Running terraform plan
(...)
Plan: 1 to add, 0 to change, 1 to destroy.

─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Saved the plan to: plan.txt

To perform exactly these actions, run the following command to apply:
    terraform apply "plan.txt"
Converting plan to JSON
Evaluating plan using Amazon Bedrock Claude 3
The following resource will be modified:

aws_instance.web: The AMI will change from ami-0e21b2eb2c48fe09a to ami-066d355e52dd737a4
## Current AMI ID
* AMI name: amzn2-ami-ecs-hvm-2.0.20240604-x86_64-ebs
* OS Architecture: AMD64 (Kernel 4.14) 
* OS Name: Amazon ECS-optimized Amazon Linux 2 AMI
* kernel: 4.14
* docker version: 20.10.25
* ECS agent: 1.83.0

## New AMI ID  
* AMI name: al2023-ami-ecs-hvm-2023.0.20240610-kernel-6.1-x86_64
* kernel: 6.1
* OS Architecture: AMD64
* OS Name: Amazon ECS-optimized Amazon Linux 2023 AMI
* docker version: 25.0.3
* ECS agent: 1.83.0
```

For additional logs, including the model "thinking" process, use teh --verbose flag:

```
python main.py --verbose eval --project-directory ./terraform
```


## Clean up

To avoid incurring additional charges, terminate the EC2 instance and delete VPC

```
cd ./terraform
terraform destroy --auto-approve
```