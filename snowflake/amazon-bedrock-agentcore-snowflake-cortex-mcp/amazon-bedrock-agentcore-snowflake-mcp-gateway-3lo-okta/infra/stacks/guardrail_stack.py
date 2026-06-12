from aws_cdk import (
    Stack, CfnOutput,
    aws_bedrock as bedrock,
)
from constructs import Construct


class GuardrailStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        prefix = self.node.try_get_context("project_prefix") or "CreditRisk3LOOkta"
        prefix_lower = prefix.lower().replace(" ", "-")

        self.guardrail = bedrock.CfnGuardrail(
            self, "Guardrail",
            name=f"{prefix_lower}-guardrail",
            description="Credit risk agent — PII redaction",
            blocked_input_messaging="I cannot process this request due to sensitive content.",
            blocked_outputs_messaging="I cannot provide this response as it may contain sensitive information.",
            sensitive_information_policy_config=bedrock.CfnGuardrail.SensitiveInformationPolicyConfigProperty(
                pii_entities_config=[
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="US_SOCIAL_SECURITY_NUMBER", action="ANONYMIZE"),
                    bedrock.CfnGuardrail.PiiEntityConfigProperty(type="CREDIT_DEBIT_CARD_NUMBER", action="ANONYMIZE"),
                ],
            ),
        )

        self.guardrail_version = bedrock.CfnGuardrailVersion(
            self, "GuardrailVersion",
            guardrail_identifier=self.guardrail.attr_guardrail_id,
            description="v1",
        )

        CfnOutput(self, "GuardrailId", value=self.guardrail.attr_guardrail_id)
        CfnOutput(self, "GuardrailVersionOutput", value=self.guardrail_version.attr_version)
