# AWSCC with Anthropic Computer Use Demo

> [!CAUTION]
> Computer use is a beta feature. Please be aware that computer use poses unique risks that are distinct from standard API features or chat interfaces. These risks are heightened when using computer use to interact with the internet. To minimize risks, consider taking precautions such as:
>
> 1. Use a dedicated virtual machine or container with minimal privileges to prevent direct system attacks or accidents.
> 2. Avoid giving the model access to sensitive data, such as account login information, to prevent information theft.
> 3. Limit internet access to an allowlist of domains to reduce exposure to malicious content.
> 4. Ask a human to confirm decisions that may result in meaningful real-world consequences as well as any tasks requiring affirmative consent, such as accepting cookies, executing financial transactions, or agreeing to terms of service.
>
> In some circumstances, Claude will follow commands found in content even if it conflicts with the user's instructions. For example, instructions on webpages or contained in images may override user instructions or cause Claude to make mistakes. We suggest taking precautions to isolate Claude from sensitive data and actions to avoid risks related to prompt injection.
>
> Finally, please inform end users of relevant risks and obtain their consent prior to enabling computer use in your own products.

## Introduction
This repository is a fork from [Anthropic QuickStarts for computer-use-demo](https://github.com/anthropics/anthropic-quickstarts). This is a demonstration on how you can get started with computer use on Claude & Amazon Bedrock, with reference implementations of:

* Build files to create a Docker container with all necessary dependencies
* A computer use agent loop using the  Bedrock to access the updated Claude 3.5 Sonnet model
* Anthropic-defined computer use tools
* A streamlit app for interacting with the agent loop
* A sample prompt to instruct agent to create new resource example in AWSCC based of inspiration of similar resource from CloudFormation page

> [!IMPORTANT]
> The Beta API used in this reference implementation is subject to change. Please refer to the [API release notes](https://docs.anthropic.com/en/release-notes/api) for the most up-to-date information.

> [!IMPORTANT]
> The components are weakly separated: the agent loop runs in the container being controlled by Claude, can only be used by one session at a time, and must be restarted or reset between sessions if necessary.

## Motivation

[AWS Cloud Control (AWSCC) Provider](https://registry.terraform.io/providers/hashicorp/awscc/latest) is a new Terraform provider for AWS, fully generated from the available CloudFormation resource schema. Since it's auto-generated, the AWSCC Terraform registry is lack on examples how to use the provider. For example, as shown [here](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/apigateway_base_path_mapping) or [here](https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/cur_report_definition).

The idea is to use generative AI to:

* Learn the AWSCC resource schema
* Equivalent resource schema and example taken from CloudFormation documentation
* Add some rules to follow
* And then generate example in AWSCC Terraform provider for the same resource

To learn more about the motivation behind this project, please check out the HashiTalks session on this subject: https://www.youtube.com/watch?v=iKujJWcnM3I&t=2253s and https://www.youtube.com/watch?v=yxpiPFruzqQ&list=PL81sUbsFNc5aJqUuK2Dkx4U53XyzBwod3&index=34 

## Development

First you need to build the new Dockerfile with Terraform, Go and Visual Studio Code installed.

You'll need to pass in AWS credentials with appropriate permissions to use Claude on Bedrock.

Don't forget to enable model access `Claude 3.5 Sonnet v2 ` in Amazon Bedrock.

```bash
./setup.sh  # configure venv, install development dependencies, and install pre-commit hooks
docker build . -t computer-use-demo:local  # manually build the docker image (required)
export AWS_PROFILE=default # change this with your AWS CLI profile
docker run \
    -e API_PROVIDER=bedrock \
    -e AWS_PROFILE=$AWS_PROFILE \
    -e AWS_REGION=us-west-2 \
    -v $HOME/.aws/credentials:/home/computeruse/.aws/credentials \
    -v $HOME/.anthropic:/home/computeruse/.anthropic \
    -p 5900:5900 \
    -p 8501:8501 \
    -p 6080:6080 \
    -p 8080:8080 \
    -it computer-use-demo:local
```

Once the container is running, see the [Generating AWSCC Example](#generating-awscc-example) section below for instructions on how to connect to the interface.

### Generating AWSCC Example

Once the container is running, open your browser to [http://localhost:8080](http://localhost:8080) to access the combined interface that includes both the agent chat and desktop view.

Use the example prompt below to experiment, feel free to change the resource name.

```
Our objective is to create example on how to use `awscc_databrew_project` using AWSCC Terraform provider.

Context about the task:

- You can find the AWSCC resource schema from: https://registry.terraform.io/providers/hashicorp/awscc/latest/docs/resources/
- You can look for the equivalent resource example in CloudFormation here: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html

Couple rules to follow:

- The attribute `policy_document` is a map of string, please use json encode.
- Change any reference to AWS account by using data source aws_caller_identity.
- Use data source for any policy document.
- Please don't use dynamic block.

Your task is:

1. Open the AWSCC schema using browser tab to review the configuration
2. Open the CloudFormation schema using new browser tab to review the configuration
3. Find the current home directory using echo $HOME
3. Create a test directory under the home directory. Use the resource name with today's date suffix as the test directory name.
4. Convert the CloudFormation example to AWSCC example
5. Run `terraform init` and then `terraform validate`
6. Fix any validation issues as needed.
7. Run `terraform fmt` to fix any formatting
8. Using terminal open the test directory in Visual Code using command `code {directory name}`. Dont forget to set the DISPLAY env var.
9. Summarize the code that you generated
```