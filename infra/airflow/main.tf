terraform {
  backend "local" {}
  required_version = ">= 1.16.4, < 1.17.0"
  required_providers {
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.17.0"
    }
  }
}

variable "kubeconfig_path" {
  type = string
}

provider "helm" {
  kubernetes {
    config_path    = var.kubeconfig_path
    config_context = "kind-banvic"
  }
}

resource "helm_release" "airflow" {
  name          = "airflow"
  namespace     = "banvic"
  repository    = "https://airflow.apache.org"
  chart         = "airflow"
  version       = "1.22.0"
  values        = [file("${path.module}/values.yaml")]
  timeout       = 900
  wait          = true
  wait_for_jobs = true
}
