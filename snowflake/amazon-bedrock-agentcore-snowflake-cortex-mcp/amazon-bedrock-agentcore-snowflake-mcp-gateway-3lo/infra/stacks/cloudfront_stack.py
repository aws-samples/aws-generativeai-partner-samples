from aws_cdk import (
    Stack, CfnOutput,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_elasticloadbalancingv2 as elbv2,
)
from constructs import Construct


class CloudFrontStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *,
                 alb: elbv2.IApplicationLoadBalancer, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk"

        # ALB origin (HTTP only — CloudFront terminates TLS at the edge)
        alb_origin = origins.HttpOrigin(
            alb.load_balancer_dns_name,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        self.distribution = cloudfront.Distribution(
            self, "Distribution",
            comment=f"{prefix} CloudFront Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=alb_origin,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=alb_origin,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                ),
            },
        )

        # --- Outputs ---
        CfnOutput(self, "DistributionDomainName",
                  value=self.distribution.distribution_domain_name)
        CfnOutput(self, "DistributionId",
                  value=self.distribution.distribution_id)
        CfnOutput(self, "CloudFrontUrl",
                  value=f"https://{self.distribution.distribution_domain_name}")
