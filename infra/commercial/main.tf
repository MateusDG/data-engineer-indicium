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
variable "kubeconfig_path" { type = string }
provider "kubernetes" {
  config_path    = var.kubeconfig_path
  config_context = "kind-banvic"
}
resource "kubernetes_service_account_v1" "commercial" {
  metadata {
    name      = "banvic-commercial"
    namespace = "banvic"
  }
  automount_service_account_token = false
}
resource "kubernetes_deployment_v1" "commercial" {
  lifecycle {
    ignore_changes = [spec[0].template[0].metadata[0].annotations["kubectl.kubernetes.io/restartedAt"]]
  }
  metadata {
    name      = "banvic-commercial"
    namespace = "banvic"
  }
  spec {
    replicas = 1
    selector {
      match_labels = { app = "banvic-commercial" }
    }
    template {
      metadata { labels = { app = "banvic-commercial" } }
      spec {
        service_account_name            = kubernetes_service_account_v1.commercial.metadata[0].name
        automount_service_account_token = false
        security_context {
          run_as_user  = 1000
          run_as_group = 1000
          fs_group     = 1000
        }
        container {
          name              = "commercial"
          image             = "banvic-commercial:1.0.0"
          image_pull_policy = "Never"
          port { container_port = 8090 }
          env_from {
            secret_ref { name = "banvic-commercial" }
          }
          resources {
            requests = { cpu = "100m", memory = "256Mi" }
            limits   = { cpu = "2", memory = "1Gi" }
          }
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = true
            capabilities {
              drop = ["ALL"]
            }
          }
          readiness_probe {
            http_get {
              path = "/health/ready"
              port = 8090
            }
            initial_delay_seconds = 5
            period_seconds        = 15
            timeout_seconds       = 25
          }
          liveness_probe {
            http_get {
              path = "/health/live"
              port = 8090
            }
            initial_delay_seconds = 30
            period_seconds        = 20
          }
          volume_mount {
            name       = "tmp"
            mount_path = "/tmp"
          }
        }
        volume {
          name = "tmp"
          empty_dir {}
        }
      }
    }
  }
}
resource "kubernetes_service_v1" "commercial" {
  metadata {
    name      = "banvic-commercial"
    namespace = "banvic"
  }
  spec {
    selector = { app = "banvic-commercial" }
    port {
      port        = 8090
      target_port = 8090
    }
  }
}
