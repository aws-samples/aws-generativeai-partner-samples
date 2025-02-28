# Refactored Bedrock Agent Test UI

This repository contains a refactored version of the AWS Bedrock Agent Test UI application. The refactoring improves code organization, maintainability, and readability by implementing modular design principles.

This directory contains the Streamlit demo application for the Splunk Bedrock Integration Suite.

## Overview

The Streamlit application provides a user-friendly interface to interact with the Bedrock integration components and demonstrate the capabilities of the system.

## Prerequisites

Before running the application, ensure you have:
1. Python 3.8 or higher installed
2. Required Python packages installed (see `requirements.txt`)
3. Proper AWS credentials configured
4. Environment variables set up correctly

## Setup

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure your AWS credentials are properly configured with appropriate permissions

3. Configure environment variables as needed

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

## Project Structure

```
├── app.py                  # Original application (for reference)
├── app_refactored.py       # Refactored main application
├── modules/                # Refactored modular components
│   ├── __init__.py         # Package initialization
│   ├── config.py           # Configuration handling
│   ├── ui.py               # UI component functions
│   └── bedrock_client.py   # AWS Bedrock service client
├── requirements.txt        # Project dependencies
└── README.md               # Project documentation
```

## Improvements Made

1. **Modular Architecture**
   - Separated concerns into dedicated modules
   - Improved code reusability and maintenance

2. **Enhanced Error Handling**
   - Structured error handling with proper logging
   - Better user feedback on errors

3. **Better Code Organization**
   - Functions are grouped by responsibility
   - Clear separation between configuration, UI rendering, and API calls

4. **Improved Documentation**
   - Added comprehensive docstrings
   - Clear function parameters and return types

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
Can you write and execute SPL to query AWS cloudtrail data. I need to see which top 5 count of non-success error code by AWS service and event. Give me a table of final results and provide your summary