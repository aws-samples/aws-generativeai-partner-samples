############### Global Variables
variable "region" {
  description = "The region of Confluent Cloud Network"
  type        = string
  default     = "us-east-1"
}

variable "prefix" {
  description = "Prefix used in all resources created"
  type        = string
  default     = "fd"
}

############### AWS Networking Variables
variable "vpc_cidr" {
  description = "VPC Cidr to be created"
  type        = string
  default     = "10.0.0.0/16"
}

variable "eks_public_access_cidrs" {
  description = "List of CIDR blocks that can access the EKS public endpoint. Set to your IP/32 for security."
  type        = list(string)
  default     = ["0.0.0.0/0"]  # Change this to your specific IP for better security
}

########## Oracle DB Variables
variable "oracle_db_name" {
  description = "Oracle DB Name"
  type        = string
  default     = "XE"
}

variable "oracle_db_username" {
  description = "Oracle DB Username"
  type        = string
  default     = "sample"
}

variable "oracle_db_password" {
  description = "Oracle DB Password"
  type        = string
  sensitive   = true
  default     = "password"
}

variable "oracle_db_port" {
  description = "Oracle DB Port"
  type        = number
  default     = 1521
}

variable "oracle_pdb_name" {
  description = "Oracle DB Name"
  type        = string
  default     = "XEPDB1"
}

variable "oracle_xstream_user_username" {
  description = "Oracle DB Username"
  type        = string
  default     = "c##cfltuser"
}

variable "oracle_xstream_user_password" {
  description = "Oracle DB Password"
  type        = string
  sensitive   = true
  default     = "password"
}

variable "oracle_xtream_outbound_server_name" {
  description = "Oracle Xstream outbound server name"
  type        = string
  default     = "xout"
}

############# Kubernetes Variables
variable "webapp_name" {
  description = "Webapp Name"
  type        = string
  default     = "fraud-demo"
}

variable "webapp_namespace" {
  description = "Kubernetes Namespace to deploy application inside"
  type        = string
  default     = "frauddemo"
}

############# OpenSearch Variables
variable "opensearch_master_username" {
  description = "OpenSearch Username"
  type        = string
  default     = "admin"
}

variable "opensearch_master_password" {
  description = "OpenSearch Password"
  type        = string
  default     = "Admin123456!"
}