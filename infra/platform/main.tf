resource "kubernetes_namespace_v1" "banvic" {
  metadata {
    name = "banvic"
  }
}

locals {
  namespace = kubernetes_namespace_v1.banvic.metadata[0].name
  volumes = {
    data = {
      path = "/banvic/data"
      size = "2Gi"
    }
    postgres = {
      path = "/banvic/postgres"
      size = "5Gi"
    }
    logs = {
      path = "/banvic/logs"
      size = "2Gi"
    }
  }
}

resource "kubernetes_persistent_volume_v1" "local" {
  for_each = local.volumes
  metadata {
    name = "banvic-${each.key}"
  }
  spec {
    capacity = {
      storage = each.value.size
    }
    access_modes                     = ["ReadWriteOnce"]
    storage_class_name               = "banvic-local"
    persistent_volume_reclaim_policy = "Retain"
    persistent_volume_source {
      host_path {
        path = each.value.path
      }
    }
    node_affinity {
      required {
        node_selector_term {
          match_expressions {
            key      = "kubernetes.io/hostname"
            operator = "In"
            values   = ["banvic-control-plane"]
          }
        }
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim_v1" "local" {
  for_each = local.volumes
  metadata {
    name      = "banvic-${each.key}"
    namespace = local.namespace
  }
  spec {
    access_modes       = ["ReadWriteOnce"]
    storage_class_name = "banvic-local"
    volume_name        = kubernetes_persistent_volume_v1.local[each.key].metadata[0].name
    resources {
      requests = {
        storage = each.value.size
      }
    }
  }
}

resource "kubernetes_service_account_v1" "pipeline" {
  metadata {
    name      = "banvic-pipeline"
    namespace = local.namespace
  }
  automount_service_account_token = false
}

resource "kubernetes_service_account_v1" "airflow" {
  metadata {
    name      = "banvic-airflow"
    namespace = local.namespace
  }
}

resource "kubernetes_role_v1" "airflow_pods" {
  metadata {
    name      = "banvic-airflow-pods"
    namespace = local.namespace
  }
  rule {
    api_groups = [""]
    resources  = ["pods", "pods/log", "pods/exec", "events"]
    verbs      = ["get", "list", "watch", "create", "delete", "patch"]
  }
}

resource "kubernetes_role_binding_v1" "airflow_pods" {
  metadata {
    name      = "banvic-airflow-pods"
    namespace = local.namespace
  }
  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "Role"
    name      = kubernetes_role_v1.airflow_pods.metadata[0].name
  }
  subject {
    kind      = "ServiceAccount"
    name      = kubernetes_service_account_v1.airflow.metadata[0].name
    namespace = local.namespace
  }
}

resource "kubernetes_config_map_v1" "postgres_init" {
  metadata {
    name      = "banvic-postgres-init"
    namespace = local.namespace
  }
  data = {
    "01-init.sh" = file("${path.module}/../postgres-init.sh")
  }
}

resource "kubernetes_service_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = local.namespace
  }
  spec {
    selector = {
      app = "banvic-postgres"
    }
    port {
      port        = 5432
      target_port = 5432
    }
  }
}

resource "kubernetes_stateful_set_v1" "postgres" {
  metadata {
    name      = "postgres"
    namespace = local.namespace
  }
  wait_for_rollout = false
  spec {
    service_name = kubernetes_service_v1.postgres.metadata[0].name
    replicas     = 1
    selector {
      match_labels = {
        app = "banvic-postgres"
      }
    }
    template {
      metadata {
        labels = {
          app = "banvic-postgres"
        }
      }
      spec {
        automount_service_account_token = false
        security_context {
          run_as_user  = 999
          run_as_group = 999
          fs_group     = 999
        }
        container {
          name              = "postgres"
          image             = "postgres:16@sha256:71e27bf60b70bded003791b5573f8b808365613f341df20ffcf0c1ed7bc13ddf"
          image_pull_policy = "IfNotPresent"
          port {
            container_port = 5432
          }
          env_from {
            secret_ref {
              name = "banvic-postgres-admin"
            }
          }
          env {
            name  = "PGDATA"
            value = "/var/lib/postgresql/data/pgdata"
          }
          volume_mount {
            name       = "postgres"
            mount_path = "/var/lib/postgresql/data"
          }
          volume_mount {
            name       = "init"
            mount_path = "/docker-entrypoint-initdb.d"
            read_only  = true
          }
          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              cpu    = "2"
              memory = "1Gi"
            }
          }
          security_context {
            allow_privilege_escalation = false
            capabilities {
              drop = ["ALL"]
            }
          }
          readiness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U postgres -d postgres"]
            }
            initial_delay_seconds = 10
            period_seconds        = 5
          }
          liveness_probe {
            exec {
              command = ["sh", "-c", "pg_isready -U postgres -d postgres"]
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }
        }
        volume {
          name = "postgres"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim_v1.local["postgres"].metadata[0].name
          }
        }
        volume {
          name = "init"
          config_map {
            name         = kubernetes_config_map_v1.postgres_init.metadata[0].name
            default_mode = "0555"
          }
        }
      }
    }
  }
}
