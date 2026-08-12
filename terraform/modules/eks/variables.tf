variable "cluster_name" {
  description = "Name of the EKS cluster."
  type        = string
  default     = "shieldops"
}

variable "kubernetes_version" {
  description = "Kubernetes version for the EKS control plane."
  type        = string
  default     = "1.32"
}

variable "environment" {
  description = "Environment this cluster belongs to (staging or production)."
  type        = string
}

variable "vpc_id" {
  description = "VPC ID from the vpc module."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs (from the vpc module) for node groups and control plane ENIs."
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs (from the vpc module), required for internet-facing ALBs the Load Balancer Controller creates."
  type        = list(string)
}

variable "node_instance_types" {
  description = "EC2 instance types for the managed node group."
  type        = list(string)
  default     = ["m5.large"]
}

variable "node_desired_size" {
  description = "Desired number of worker nodes."
  type        = number
  default     = 2
}

variable "node_min_size" {
  description = "Minimum number of worker nodes."
  type        = number
  default     = 2
}

variable "node_max_size" {
  description = "Maximum number of worker nodes."
  type        = number
  default     = 6
}

variable "tags" {
  description = "Tags applied to all resources in this module."
  type        = map(string)
  default     = {}
}