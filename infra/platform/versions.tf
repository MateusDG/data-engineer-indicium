terraform {
  backend "local" {}
  required_version = ">= 1.16.4, < 1.17.0"
  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.38.0"
    }
  }
}

provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = "kind-banvic"
}

variable "kubeconfig_path" {
  type = string
}
