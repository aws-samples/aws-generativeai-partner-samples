# AWS Generative AI with Datadog Observability

This repository contains samples and reference architectures for integrating Datadog observability with AWS Generative AI services. These samples demonstrate how to implement comprehensive monitoring, tracing, and observability for GenAI applications running on AWS.

## Overview

Building generative AI applications on AWS provides powerful capabilities, but ensuring these applications are observable, performant, and reliable requires proper monitoring. This project showcases how to integrate Datadog's observability platform with various AWS GenAI services to gain insights into your applications' behavior, performance, and health.

## AWS GenAI Services Covered

- **Amazon Bedrock**: Samples for monitoring foundation model inference with Datadog
- **Amazon Bedrock Agents**: Observability patterns for Bedrock Agents
- **Model Context Protocol (MCP)**: Tracing and monitoring for MCP-based applications
- **Amazon Strands**: Integration examples with Datadog for Strands applications

## Key Features

- End-to-end distributed tracing for GenAI applications
- Custom metrics and dashboards for model performance monitoring
- Latency and throughput tracking for AI/ML workloads
- Cost optimization insights for GenAI services
- Anomaly detection for model behavior
- Log correlation with traces for troubleshooting

## Prerequisites

- AWS Account with access to GenAI services
- Datadog account with API key
- Python 3.8+ for sample applications
- AWS CLI configured with appropriate permissions
- Docker (for containerized samples)

Some examples in this repository support OpenTelemetry (OTEL) tracing directly. While Datadog does not yet provide a public endpoint for submitting OTEL traces, you can use the [adot-collector-datadog](https://github.com/jasonmimick-aws/adot-collector-datadog) project to bridge this gap. This collector can be deployed to receive OTEL traces from your applications and forward them to Datadog, enabling full observability while using the OpenTelemetry standard.



## Sample Projects

### Bedrock Model Inference with Datadog Tracing

Demonstrates how to instrument Amazon Bedrock API calls with Datadog's APM to track model performance, latency, and costs.

### Bedrock Agents Observability

Shows how to implement observability for Bedrock Agents, including custom metrics for agent performance and tracing for agent actions.

- [Simple Bedrock Agent with Datadog](https://github.com/jasonmimick-aws/simple-bedrock-agent-datadog) - A reference implementation demonstrating how to instrument Amazon Bedrock Agents with Datadog observability, providing insights into agent performance, latency, and behavior.

### MCP Integration with Datadog

Examples of monitoring Model Context Protocol applications with Datadog, including distributed tracing across MCP server boundaries.

- [Datadog MCP Server for Amazon Q](https://github.com/jasonmimick-aws/datadog-mcp-amazon-q) - A Model Context Protocol server that integrates Datadog observability with Amazon Q, enabling tracing and monitoring of LLM interactions.
- [Amazon Bedrock Agent MCP Demo](https://github.com/jasonmimick-aws/amazon-bedrock-agent-mcp-demo) - Demonstrates how to use Model Context Protocol with Amazon Bedrock Agents and implement observability using Datadog.

### Strands with Datadog Monitoring

Reference implementation for monitoring Amazon Strands applications with Datadog, focusing on performance metrics and error tracking.

- [Strands Agents with Datadog Integration](https://github.com/jasonmimick-aws/strands-agents-samples/tree/main/03-integrations/datadog) - Demonstrates how to implement observability for Amazon Strands Agents using Datadog, providing insights into agent performance, interactions, and error handling.

## Architecture

Each sample includes architecture diagrams showing how Datadog integrates with the AWS GenAI services. The general pattern involves:

1. Instrumenting application code with Datadog's tracing libraries
2. Configuring custom metrics for model-specific monitoring
3. Setting up dashboards and alerts for key performance indicators
4. Implementing log correlation with traces for comprehensive debugging

## Best Practices

- Use service tags consistently across all telemetry data
- Implement custom metrics for model-specific performance indicators
- Set up alerts for abnormal latency or error rates
- Correlate traces with logs for efficient troubleshooting
- Monitor cost metrics to optimize GenAI service usage

## Contributing

Contributions to improve existing samples or add new ones are welcome! Please see CONTRIBUTING.md for details.

## License

This project is licensed under the MIT No Attribution License - see the LICENSE file in the parent directory for details.

## Resources

- [Datadog AWS Integration Documentation](https://docs.datadoghq.com/integrations/amazon_web_services/)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Datadog APM Documentation](https://docs.datadoghq.com/tracing/)
- [AWS Generative AI Resources](https://aws.amazon.com/generative-ai/)
