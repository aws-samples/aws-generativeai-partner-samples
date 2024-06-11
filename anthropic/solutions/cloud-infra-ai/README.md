# Cloud Infra AI

Application that integrates with terraform plans to provides additional information of changes that are related to Elastic Container Service AMIs with tool use, Amazon Bedrock and Anthropic Claude 3 Sonnet

## Prerequisites

* Python3
* An AWS account with access to Claude3 sonnet
* Terraform


## Installation

1. Clone this repo and navigate to the cloud-infra-ai folder
```
git clone https://github.com/aws-samples/aws-generativeai-partner-samples.git
cd aws-generativeai-partner-samples/solutions/cloud-infra-ai
```

2. Install requirements

Optional - Create a virtual environment
```
python3 -m virtualenv .env
source .env/bin/activate
```

Install requirements
```
pip install requirements.txt
```

Test
```
% python main.py --help
Usage: main.py [OPTIONS] COMMAND [ARGS]...

Options:
  --verbose  Print detailed information in output besides the final report
  --help     Show this message and exit.

Commands:
  eval
```

## Usage example

1. The application requires a terraform project. The following steps use the ec2 core-infra example are at https://github.com/aws-ia/ecs-blueprints. 

```
git clone https://github.com/aws-ia/ecs-blueprints.git
cd ecs-blueprints/terraform/ec2-examples/core-infra
terraform apply
```

2. Once applied, modify the ECS AMI - this will be detected by the app. Open the ecs-blueprints/terraform/ec2-examples/core-infra/main.tf file and replace line 110 for 

```
  name = "/aws/service/ecs/optimized-ami/amazon-linux-2/amzn2-ami-ecs-hvm-2.0.20240604-x86_64-ebs"
```

3. Run the application - the AMI details fetched using tool use with Claude 3 should be in the output

_Note: Make sure to navigate to the aws-generativeai-partner-samples/solutions/cloud-infra-ai before executing the following command_

```
% python main.py eval --project-directory ./ecs-blueprints/terraform/ec2-examples/core-infra
Running terraform plan
(...)

  # module.autoscaling.aws_launch_template.this[0] will be updated in-place
  ~ resource "aws_launch_template" "this" {
        id                      = "lt-12345678"
      ~ image_id                = (sensitive value)
      ~ latest_version          = 1 -> (known after apply)
        name                    = "core-infra-12345678"
        tags                    = {
            "Blueprint"  = "core-infra"
            "GithubRepo" = "github.com/aws-ia/ecs-blueprints"
        }
        # (10 unchanged attributes hidden)

        # (2 unchanged blocks hidden)
    }

Plan: 0 to add, 2 to change, 0 to destroy.

─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

Saved the plan to: plan.txt

To perform exactly these actions, run the following command to apply:
    terraform apply "plan.txt"
Converting plan to JSON
Evaluating plan using Amazon Bedrock Claude 3
The following resource will be modified:

aws_launch_template.this[0] (module.autoscaling)
  Old AMI ID: ami-0ca918c886e7b7539
  New AMI ID: ami-0cdea3b9c163c70ae
## Current AMI ID
* AMI name: al2023-ami-ecs-hvm-2023.0.20240604-kernel-6.1-x86_64
* OS Architecture: AMD64
* OS Name: Amazon ECS-optimized Amazon Linux 2023 AMI
* kernel: 6.1
* docker version: 25.0.3
* ECS agent: 1.83.0

## New AMI ID  
* AMI name: amzn2-ami-ecs-hvm-2.0.20240604-x86_64-ebs
* kernel: 4.14
* OS Architecture: AMD64 (Kernel 4.14)
* OS Name: Amazon ECS-optimized Amazon Linux 2 AMI
* docker version: 20.10.25
* ECS agent: 1.83.0
```
