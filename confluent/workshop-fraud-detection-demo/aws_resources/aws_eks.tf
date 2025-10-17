

resource "aws_iam_role" "node" {
  name = "eks-auto-node-example-${random_id.env_display_id.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = ["sts:AssumeRole"]
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "node_AmazonEKSWorkerNodeMinimalPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodeMinimalPolicy"
  role       = aws_iam_role.node.name
}

resource "aws_iam_role_policy_attachment" "node_AmazonEC2ContainerRegistryPullOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPullOnly"
  role       = aws_iam_role.node.name
}

# IAM policy for pulling from public ECR
resource "aws_iam_policy" "node_ecr_public_pull" {
  name        = "eks-node-ecr-public-pull-${random_id.env_display_id.hex}"
  description = "Allow EKS nodes to pull images from public ECR"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr-public:GetAuthorizationToken",
          "sts:GetServiceBearerToken",
          "ecr-public:BatchCheckLayerAvailability",
          "ecr-public:GetRepositoryPolicy",
          "ecr-public:DescribeRepositories",
          "ecr-public:DescribeImages",
          "ecr-public:GetDownloadUrlForLayer",
          "ecr-public:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "node_ecr_public_pull" {
  policy_arn = aws_iam_policy.node_ecr_public_pull.arn
  role       = aws_iam_role.node.name
}

resource "aws_iam_role" "cluster" {
  name = "eks-cluster-example-${random_id.env_display_id.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sts:AssumeRole",
          "sts:TagSession"
        ]
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSComputePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSComputePolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSBlockStoragePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSBlockStoragePolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSLoadBalancingPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSLoadBalancingPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_AmazonEKSNetworkingPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSNetworkingPolicy"
  role       = aws_iam_role.cluster.name
}

data "aws_caller_identity" "current" {}

locals {
  caller_arn = data.aws_caller_identity.current.arn
  caller_arn_parts = split(":", local.caller_arn)
  
  # Determine if this is an assumed role (contains "sts" and "assumed-role") or regular IAM user/role
  is_assumed_role = local.caller_arn_parts[2] == "sts" && contains(split("/", local.caller_arn_parts[5]), "assumed-role")
  
  # For assumed roles, convert to IAM role ARN. For IAM users/roles, keep as is.
  principal_arn = local.is_assumed_role ? (
    # Convert assumed-role ARN to IAM role ARN
    "arn:aws:iam::${local.caller_arn_parts[4]}:role/${split("/", local.caller_arn_parts[5])[1]}"
  ) : (
    # For IAM users/roles, keep the original ARN
    local.caller_arn
  )
}

# KMS key for EKS secrets encryption
resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS secrets encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow EKS to use the key"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant"
        ]
        Resource = "*"
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-eks-kms-${random_id.env_display_id.hex}"
  }
}

resource "aws_kms_alias" "eks" {
  name          = "alias/${var.prefix}-eks-${random_id.env_display_id.hex}"
  target_key_id = aws_kms_key.eks.key_id
}

# ################################################################
# # EKS INFRA
# ################################################################
resource "aws_eks_cluster" "eks_cluster" {
  name     = "${var.prefix}-eks-cluster-${random_id.env_display_id.hex}"
  role_arn = aws_iam_role.cluster.arn
  version = "1.31"
  bootstrap_self_managed_addons = false

  # Enable secrets encryption
  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  # Enable control plane logging
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  compute_config {
    enabled = true
    node_pools = ["general-purpose"]
    node_role_arn = aws_iam_role.node.arn
  }

  kubernetes_network_config {
    elastic_load_balancing {
      enabled = true
    }
  }

  storage_config {
    block_storage {
      enabled = true
    }
  }

  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }

  vpc_config {
    subnet_ids = [for subnet in aws_subnet.private_subnets : subnet.id]
    endpoint_public_access = true
    endpoint_private_access = true
    public_access_cidrs = var.eks_public_access_cidrs
  }


  tags = {
    Name = "${var.prefix}-eks-cluster-${random_id.env_display_id.hex}"
  }

  # Ensure that IAM Role permissions are created before and deleted
  # after EKS Cluster handling. Otherwise, EKS will not be able to
  # properly delete EKS managed EC2 infrastructure such as Security Groups.
  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSComputePolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSBlockStoragePolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSLoadBalancingPolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSNetworkingPolicy,
  ]

}