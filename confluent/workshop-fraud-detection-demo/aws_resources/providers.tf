terraform {
    required_providers {
        aws = {
            source  = "hashicorp/aws"
            version = "5.84"
        }
        kubernetes = {
          source  = "hashicorp/kubernetes"
          version = "2.35.1"
        }
    }
}


provider "kubernetes" {
  host                   = aws_eks_cluster.eks_cluster.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.eks_cluster.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", aws_eks_cluster.eks_cluster.name]
  }
}

provider "aws" {
  region = var.region
}
