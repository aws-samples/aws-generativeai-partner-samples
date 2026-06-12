from aws_cdk import (
    Stack, CfnOutput, RemovalPolicy,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_ecr_assets as ecr_assets,
    aws_elasticloadbalancingv2 as elbv2,
    aws_logs as logs,
)
from constructs import Construct
import os


class WebAppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *,
                 ecs_exec_role_arn: str, ecs_task_role_arn: str,
                 user_pool, app_client, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk3LOOkta"
        prefix_lower = prefix.lower().replace(" ", "-")
        project_dir = os.path.join(os.path.dirname(__file__), "..", "..")

        # Import roles by ARN to avoid cross-stack cyclic dependencies
        exec_role = iam.Role.from_role_arn(self, "ExecRole", ecs_exec_role_arn, mutable=False)
        task_role = iam.Role.from_role_arn(self, "TaskRole", ecs_task_role_arn, mutable=False)

        # Cognito IDs must be concrete strings for Docker build args (React bakes
        # process.env.REACT_APP_* at build time). These come from cdk.json context,
        # which must be set after deploying the Cognito stack (Phase 4) and before
        # deploying the WebApp stack (Phase 7).
        cognito_pool_id = self.node.try_get_context("cognito_pool_id") or ""
        cognito_client_id = self.node.try_get_context("cognito_client_id") or ""

        # Validate — use Aspects to defer validation to synth time for this stack only
        _missing = []
        if not cognito_pool_id or "REPLACE" in cognito_pool_id.upper():
            _missing.append("cognito_pool_id")
        if not cognito_client_id or "REPLACE" in cognito_client_id.upper():
            _missing.append("cognito_client_id")
        if _missing:
            from aws_cdk import Annotations
            Annotations.of(self).add_error(
                f"Missing in cdk.json: {', '.join(_missing)}. "
                f"Deploy Cognito stack first (Phase 4), then set these values (Phase 5) "
                f"before deploying WebApp (Phase 7). See CDK_DEPLOYMENT_GUIDE.md."
            )
            # Use placeholder to allow synth of other stacks to proceed
            cognito_pool_id = cognito_pool_id or "MISSING"
            cognito_client_id = cognito_client_id or "MISSING"

        # --- VPC (default) ---
        vpc = ec2.Vpc.from_lookup(self, "Vpc", is_default=True)

        # --- ECS Cluster ---
        cluster = ecs.Cluster(self, "Cluster",
            cluster_name=f"{prefix_lower}-cluster", vpc=vpc)

        # --- Log Group ---
        log_group = logs.LogGroup(self, "LogGroup",
            log_group_name=f"/ecs/{prefix_lower}",
            removal_policy=RemovalPolicy.DESTROY)

        # --- Docker Image Assets ---
        frontend_image = ecr_assets.DockerImageAsset(self, "FrontendImage",
            directory=os.path.join(project_dir, "webapp", "frontend"),
            build_args={
                "REACT_APP_COGNITO_POOL_ID": cognito_pool_id,
                "REACT_APP_COGNITO_CLIENT_ID": cognito_client_id,
            },
        )
        backend_image = ecr_assets.DockerImageAsset(self, "BackendImage",
            directory=os.path.join(project_dir, "webapp", "backend"),
        )

        # --- Task Definition (2 containers) ---
        task_def = ecs.FargateTaskDefinition(self, "TaskDef",
            cpu=1024, memory_limit_mib=3072,
            execution_role=exec_role,
            task_role=task_role,
        )

        task_def.add_container("frontend",
            image=ecs.ContainerImage.from_docker_image_asset(frontend_image),
            essential=True,
            port_mappings=[ecs.PortMapping(container_port=80)],
            logging=ecs.LogDrivers.aws_logs(stream_prefix="frontend", log_group=log_group),
        )

        task_def.add_container("backend",
            image=ecs.ContainerImage.from_docker_image_asset(backend_image),
            essential=True,
            port_mappings=[ecs.PortMapping(container_port=8000)],
            environment={
                "AGENT_RUNTIME_ARN": self.node.try_get_context("agent_runtime_arn") or "PLACEHOLDER",
                "USER_POOL_ID": user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": app_client.user_pool_client_id,
                "ALLOWED_ORIGIN": "*",  # Tightened at runtime via deploy.sh or ECS env override
                "AWS_DEFAULT_REGION": self.region,
                "GATEWAY_URL": self.node.try_get_context("gateway_url") or "PLACEHOLDER",
            },
            logging=ecs.LogDrivers.aws_logs(stream_prefix="backend", log_group=log_group),
        )

        # --- ALB (exposed for CloudFront stack) ---
        self.alb = elbv2.ApplicationLoadBalancer(self, "ALB",
            load_balancer_name=f"{prefix_lower}-alb",
            vpc=vpc, internet_facing=True)

        # open=False suppresses CDK's auto-generated 0.0.0.0/0 ingress rule
        listener = self.alb.add_listener("HttpListener", port=80, open=False)

        # Restrict ALB to CloudFront-only traffic via AWS managed prefix list.
        # Dynamic lookup = portable across regions (IDs like pl-3b927c52 are region-specific).
        cloudfront_pl = ec2.PrefixList.from_lookup(
            self, "CloudFrontPL",
            prefix_list_name="com.amazonaws.global.cloudfront.origin-facing",
        )
        self.alb.connections.security_groups[0].add_ingress_rule(
            ec2.Peer.prefix_list(cloudfront_pl.prefix_list_id),
            ec2.Port.tcp(80),
            "CloudFront origin-facing only",
        )
        ecs_sg = ec2.SecurityGroup(self, "EcsSG", vpc=vpc,
            description="ECS tasks SG", allow_all_outbound=True)
        ecs_sg.add_ingress_rule(self.alb.connections.security_groups[0],
            ec2.Port.tcp(80), "ALB to frontend")
        ecs_sg.add_ingress_rule(self.alb.connections.security_groups[0],
            ec2.Port.tcp(8000), "ALB to backend")

        # --- ECS Service ---
        service = ecs.FargateService(self, "Service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=1,
            assign_public_ip=True,  # Required for Fargate in default VPC without NAT gateway
            security_groups=[ecs_sg],
        )

        # --- Target Groups (frontend default, backend for /api/*) ---
        listener.add_targets("FrontendTG",
            port=80, protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service.load_balancer_target(container_name="frontend", container_port=80)],
            health_check=elbv2.HealthCheck(path="/"),
        )

        listener.add_targets("BackendTG",
            port=8000, protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[service.load_balancer_target(container_name="backend", container_port=8000)],
            conditions=[elbv2.ListenerCondition.path_patterns(["/api/*"])],
            priority=10,
            health_check=elbv2.HealthCheck(path="/api/health"),
        )

        # --- Outputs ---
        CfnOutput(self, "AlbDnsName", value=self.alb.load_balancer_dns_name)
        CfnOutput(self, "AlbUrl", value=f"http://{self.alb.load_balancer_dns_name}")
