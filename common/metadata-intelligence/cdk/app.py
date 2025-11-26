#!/usr/bin/env python3
import aws_cdk as cdk
from aurora_opensearch_stack import AuroraOpenSearchStack

app = cdk.App()
AuroraOpenSearchStack(app, "AuroraOpenSearchStack")
app.synth()