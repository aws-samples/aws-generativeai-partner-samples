resource "kubernetes_namespace" "demo_namespace" {
  metadata {
    name = var.webapp_namespace
  }
  depends_on = [aws_eks_cluster.eks_cluster]
}

# Generate random password for Kubernetes admin user
resource "random_password" "k8s_admin_password" {
  length  = 16
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "kubernetes_config_map" "fraud_demo_config" {
  metadata {
    name = "${var.webapp_name}-config"
    namespace = kubernetes_namespace.demo_namespace.metadata[0].name
  }
  data = {
    DB_HOST = aws_instance.oracle_instance.private_ip
    DB_PORT = var.oracle_db_port
    DB_NAME = var.oracle_pdb_name
    DB_USER = var.oracle_db_username
    DB_PASSWORD = random_password.oracle_db_password.result
    ADMIN_USER_USERNAME = "admin"
    ADMIN_USER_EMAIL = "admin@admin.com"
    ADMIN_USER_PASSWORD = random_password.k8s_admin_password.result
  }
  depends_on = [aws_instance.oracle_instance, aws_eks_cluster.eks_cluster]
}

resource "kubernetes_deployment" "fraud_demo" {
  metadata {
    name = "${var.webapp_name}"
    namespace = kubernetes_namespace.demo_namespace.metadata[0].name
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        "app.kubernetes.io/name" = "${var.webapp_name}"
      }
    }

    template {
      metadata {
        labels = {
          "app.kubernetes.io/name" = "${var.webapp_name}"
        }
      }

      spec {
        # Pod security context
        security_context {
          run_as_non_root = true
          run_as_user     = 1000
          fs_group        = 1000
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }

        container {
          name  = "${var.webapp_name}"
          image = "public.ecr.aws/v3a9u0p7/demo/fraud-webapp:latest"
          image_pull_policy = "Always"
          command = [
            "/bin/sh",
            "-c"
          ]

          args = [
            <<-EOT
              python /opt/fraud_detection/manage.py makemigrations &&
              python /opt/fraud_detection/manage.py migrate &&
              python /opt/fraud_detection/manage.py collectstatic --no-input &&
              python /opt/fraud_detection/manage.py load_users &&
              python /opt/fraud_detection/manage.py create_default_super_user &&
              gunicorn -c /opt/fraud_detection/gunicorn.conf.py fraud_detection.wsgi:application
            EOT
          ]

          # Container security context
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = false
            run_as_non_root            = true
            run_as_user                = 1000
            capabilities {
              drop = ["ALL", "NET_RAW"]
            }
          }

          # Resource limits and requests
          resources {
            limits = {
              cpu    = "1000m"
              memory = "1Gi"
            }
            requests = {
              cpu    = "250m"
              memory = "256Mi"
            }
          }

          port {
            name           = "gunicornport"
            container_port = 8000
          }

          # Volume mount for staticfiles (writable by user 1000)
          volume_mount {
            name       = "staticfiles"
            mount_path = "/opt/fraud_detection/staticfiles"
          }

          liveness_probe {
            http_get {
              path = "/health/"
              port = 8000
            }

            initial_delay_seconds = 3
            period_seconds        = 10
            timeout_seconds       = 2
            failure_threshold     = 5
          }

          readiness_probe {
            http_get {
              path = "/health/"
              port = 8000
            }

            initial_delay_seconds = 20
            period_seconds        = 3
            timeout_seconds       = 3
            failure_threshold     = 5
          }

          env {
            name = "DB_NAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "DB_NAME"
              }
            }
          }

          env {
            name = "DB_USER"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "DB_USER"
              }
            }
          }

          env {
            name = "DB_HOST"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "DB_HOST"
              }
            }
          }

          env {
            name = "DB_PORT"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "DB_PORT"
              }
            }
          }

          env {
            name = "DB_PASSWORD"
            value_from {
              config_map_key_ref { 
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "DB_PASSWORD"
              }
            }
          }

          env {
            name = "ADMIN_USER_USERNAME"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "ADMIN_USER_USERNAME"
              }
            }
          }

          env {
            name = "ADMIN_USER_EMAIL"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "ADMIN_USER_EMAIL"
              }
            }
          }

          env {
            name = "ADMIN_USER_PASSWORD"
            value_from {
              config_map_key_ref {
                name = kubernetes_config_map.fraud_demo_config.metadata[0].name
                key  = "ADMIN_USER_PASSWORD"
              }
            }
          }
        }

        # Volume definition for staticfiles
        volume {
          name = "staticfiles"
          empty_dir {}
        }
      }
    }
  }

  depends_on = [aws_instance.oracle_instance]
}

resource "kubernetes_service" "fraud_demo_service" {
  metadata {
    name = "service-${var.webapp_name}"
    namespace = kubernetes_namespace.demo_namespace.metadata[0].name
  }

  spec {
    type = "NodePort"
    selector = {
      "app.kubernetes.io/name" = kubernetes_deployment.fraud_demo.metadata[0].name
    }
    port {
      protocol = "TCP"
      port        = 8080
      target_port = 8000
    }
  }
  depends_on = [kubernetes_deployment.fraud_demo]

}

resource "kubernetes_ingress_class" "fraud_demo_load_balancer_controller" {
  metadata {
    labels = {
       "app.kubernetes.io/name" = "LoadBalancerController"
    }
    name = "alb"
  }
  spec {
    controller = "eks.amazonaws.com/alb"
  }
}

resource "kubernetes_ingress_v1" "fraud_demo_load_balancer" {
  wait_for_load_balancer = true
  metadata {
    name = "ingress-${var.webapp_name}"
    namespace = kubernetes_namespace.demo_namespace.metadata[0].name
    annotations = {
      "alb.ingress.kubernetes.io/scheme" = "internet-facing"
      "alb.ingress.kubernetes.io/target-type" = "ip"
    }
  }
  spec {
    ingress_class_name = kubernetes_ingress_class.fraud_demo_load_balancer_controller.metadata[0].name
    rule {
      http {
        path {
          path = "/*"
          backend {
            service {
              name = kubernetes_service.fraud_demo_service.metadata[0].name
            port {
              number = kubernetes_service.fraud_demo_service.spec[0].port[0].port
            }
            }
          }
        }
      }
    }
  }
}

# Display load balancer hostname (typically present in AWS)
output "demo_details" {
  value = {
    fraud_ui = "http://${kubernetes_ingress_v1.fraud_demo_load_balancer.status.0.load_balancer.0.ingress.0.hostname}/fraud-demo/"
  }
}
