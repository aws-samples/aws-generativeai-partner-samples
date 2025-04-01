## Overview

The Streamlit application provides a user-friendly interface to interact with the Bedrock Agent for Splunk Assistant

## Prerequisites

Before running the application, ensure you have:
1. Python 3.8 or higher installed
2. Required Python packages installed (see `requirements.txt`)
3. Proper AWS credentials configured
4. Environment variables set up correctly
5. Bedrock Agent should be created. Following the instructions from ../README.md to deploy bedrock agent using CDK.
5. Update the .env file and provide agent_id and agent_alias_id

Capture the following outputs from BedrockAgentStack and replace them in the .env in the streamlitapp
For example, if your CDK output is shown as below:
```
   BedrockAgentStack.BedrockAgentAlias = 7D5OBAYQUT|R4KHCSUTXD
   BedrockAgentStack.BedrockAgentID = 7D5OBAYQUT
```

Then edit your `.env` file as below:
```
# Environment variables for streamlit app
# Replace AGENT_ID and AGENT_ALIAS_ID
LOG_LEVEL=INFO
BEDROCK_AGENT_ID=7D5OBAYQUT
BEDROCK_AGENT_ALIAS_ID=R4KHCSUTXD
```


## Setup

1. Install required dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Ensure your AWS credentials are properly configured with appropriate permissions 

3. Configure environment variables as needed 
   ```bash
   export AWS_ACCESS_KEY_ID=<YOUR AWS ACCESS KEY>
   export AWS_SECRET_ACCESS_KEY=<YOUR AWS SECRET ACCESS KEY>
   export AWS_SESSION_TOKEN=<YOUR AWS SESSION TOKEN>
   ```

## How to Run
You can run the application using either of these methods:

1. Using the run script:
   ```bash
   ./run.sh
   ```

2. Direct Streamlit command:
   ```bash
   streamlit run app.py
   ```

The Streamlit app will be available at:
- Local: http://localhost:8501


## Project Structure

- `app.py`: Main Streamlit application file
- `bedrock_agent_runtime.py`: Handles Bedrock agent interactions
- `requirements.txt`: Lists all Python dependencies
- `run.sh`: Convenience script to start the application
- `setup.sh`: Setup script for initial configuration

## Logging

The application uses a YAML-based logging configuration. Ensure the `logging.yaml` file is present in the directory.

## Contributing

When contributing to this application, please ensure to:
1. Follow the existing code style
2. Update documentation as needed
3. Test your changes thoroughly before submitting

## Troubleshooting

If you encounter issues:
1. Verify AWS credentials are properly configured
2. Check all required environment variables are set
3. Ensure all dependencies are installed correctly
4. Review the application logs for specific error messages


## Sample Query
Write a SPL to query the AWS CloudTrail data, get list of top 10 AWS events and summarize the result.