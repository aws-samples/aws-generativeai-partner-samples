## Terraform plan analyzer run task

Integrate Amazon Bedrock with HCP Terraform (previously Terraform Cloud) workflows using run tasks to:

* Analyze Terraform plan and generate summary
* Function call for other API-based analysis (e.g AMI analysis)

Getting started:

1. Run the Terraform in [setup](./setup/) folder to deploy the pre-requisite infrastructure
    ```
    cd setup/
    terraform init
    terraform apply
    ```
2. Then run the Terraform in [example](./example/) folder that demonstrates the Terraform plan analysis for an example configuration using Amazon Bedrock
    ```
    cd example/
    terraform init
    terraform apply
    ```

To explore the complete list of available configuration options checkout the Terraform module in the [Terraform registry](https://registry.terraform.io/modules/aws-ia/runtask-tf-plan-analyzer/aws/latest)
