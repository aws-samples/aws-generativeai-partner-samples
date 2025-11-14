# Bedrock AgentCore Strands Playground

Read [this document](./agentcore_playground.md) for background.

## Features

- **Dynamic tool and model selection:** change available tools and model on the fly
- **Authentication:** uses Cognito to authenticate user to the agent
- **Real-time Chat Interface**: Interactive chat with deployed AgentCore agents
- **Agent Discovery**: Automatically discover and select from available agents in your AWS account
- **Version Management**: Choose specific versions of your deployed agents
- **Multi-Region Support**: Connect to agents deployed in different AWS regions
- **Streaming Responses**: Real-time streaming of agent responses
- **Session Management**: Maintain conversation context with unique session IDs
- **Memory Management**: Uses AgentCore Memory to save user preferences and conversation context

## Architecture

![AgentCore Architecture](./images/BRAC_architecture.png)

## Prerequisites

- Python 3.11 or higher
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- AWS CLI configured with appropriate credentials
- Access to Amazon Bedrock AgentCore service
- Deployed agents on Bedrock AgentCore Runtime
- Optional: Cognito [user pool](https://github.com/awslabs/amazon-bedrock-agentcore-samples/blob/main/01-tutorials/03-AgentCore-identity/03-Inbound%20Auth%20example/inbound_auth_runtime_with_strands_and_bedrock_models.ipynb./COGNITO_SETUP.m)

### Required AWS Permissions

Your AWS credentials need the following permissions:

- `bedrock-agentcore-control:ListAgentRuntimes`
- `bedrock-agentcore-control:ListAgentRuntimeVersions`
- `bedrock-agentcore:InvokeAgentRuntime`
  Note that other permissions may be required by tools you select.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/aws-samples/aws-generativeai-partner-samples/tree/main/agentcore-strands-playground
   ```
2. **Install dependencies using uv**:

   ```bash
   uv sync
   ```

## Deploy the Example Agent

1. **Configure the agent**:

```bash
cd agentcore_agent
uv run agentcore configure -e runtime_agent.py
```

Select default options, except optionally configure your Cognito pool as OAuth authorizer (or other OAuth provider), and configure Long Term Memory under Memory Configuration.

2. **Deploy to AgentCore Runtime:**

uv run agentcore launch
cd ..

## Running the Application

### Using uv (recommended)

```bash
uv run streamlit run app.py [-- --auth | --noauth]
```

The application will start and be available at `http://localhost:8501`.

If you configured a Cognito pool for authentication, the app will automatically look in 1) .env file and 2) ./agentcore_agent/.bedrock_agentcore.yaml to find Cognito configuration variables. If it finds a Cognito configuration, or if you specify '--auth' on the command line, it will default to using authentication when invoking the agent. If it does not find Cognito configuration, or if you specify '--noauth' on the command line, it will not use any authentication when invoking the agent.

Note: many of the Strands built-in tools require permissions that are not automatically granted to the execution role, because the AgentCore Starter Toolkit follows security best practices and grants least privilege access. For example, the prompt "use aws to list s3 buckets" will fail even if the 'use_aws' tool is configured in the Tool Selection panel because the AgentCore runtime role does not have appropriate permissions. To grant permissions, determine the role name (available in ./agentcore_agent/.bedrock_agentcore.yaml) and attach relevant policies to the role. For example:

```
aws iam attach-role-policy \
    --role-name AmazonBedrockAgentCoreSDKRuntime-us-west-2-xxxxxx \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess
```

## Usage

Note: all parameters have defaults, which typically pick the most recent agent/version/session. The simplest usage is to run the front-end application and start chatting with the agent.

Optional:

1. **Configure Tools:** Click the Tools Configuration dropdown to select from available Strands Agents built-in tools
2. **Configure AWS Region**: Select your preferred AWS region from the sidebar
3. **Select Agent**: Choose from automatically discovered agents in your account
4. **Choose Version**: Select the specific version of your agent to use
5. **Select Memory**: The front-end will discover configured AgentCore Memory resources and select the most recently created
6. **Select Session:** Choose from a saved session or enter a new session name and click "New session"
7. **Select Tools:**
8. **Start Chatting**: Type your message in the chat input and press Enter

## Project Structure

```
agentcore-strands-playground/
├── app.py                           # Main Streamlit application
├── auth_utils.py                    # Cognito authentication utilities
├── br_utils.py                      # Bedrock utilities (model discovery)
├── dotenv.example                   # Example environment variables
├── pyproject.toml                   # Project dependencies (uv)
├── README.md                        # This file
├── agentcore_agent/                 # Agent deployment configuration
│   ├── runtime_agent.py             # Strands agent implementation
│   ├── requirements.txt             # Agent dependencies
├── images/                          # Documentation images
│   ├── BRAC_architecture.png
│   ├── BRAC_interface_screen.png
│   └── ...
└── static/                          # UI assets (fonts, icons, logos)
    ├── agentcore-service-icon.png
    ├── gen-ai-dark.svg
    ├── user-profile.svg
    └── ...
```

## Configuration Files

- **`pyproject.toml`**: Defines project dependencies and metadata

## Troubleshooting

### Common Issues

1. **No agents found**: Ensure you have deployed agents in the selected region and have proper AWS permissions
2. **Connection errors**: Verify your AWS credentials and network connectivity
3. **Permission denied**: Check that your IAM user/role has the required Bedrock AgentCore permissions

### Debug Mode

Enable debug logging by setting the Streamlit logger level in the application or check the browser console for additional error information.

## Development

### Adding New Features

The application is built with modularity in mind, particularly the ability for AWS partners to add funcationality. Key areas for extension:

- **Partner LLMs**: the list of LLMs returned in br_utils.py can be modified
- **Observability**: the agent is configured to report OTEL logs which can be consumed by partner observability solutions
- **Identity**: the auth_utils.py module can be replaced by a partner IdP solution
- **Partner Memory**: the memory interface can be modified to use different partner tools
- **MCP Servers**: any partner MCP server can be called by the agent

### Dependencies

- **boto3**: AWS SDK for Python
- **streamlit**: Web application framework
- **uv**: Fast Python package installer and resolver

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the terms specified in the repository license file.

## Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [Bedrock AgentCore Samples](https://github.com/awslabs/amazon-bedrock-agentcore-samples/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Strands Agents Framework](https://github.com/awslabs/strands-agents)
  Agent
