# About PAIG Quick Start

This example application demonstrates how to integrate PAIG SecureVigil with your GenAI application. This 
example application uses AWS Bedrock along with the LLM model it supports.

## **Use Cases**

Primary use cases for this example application include:

1. Integration with PAIG with sample GenAI application.
2. Using AWS Bedrock to call the LLM models
3. Detecting PII and sensitive data in the prompts and replies.
4. Optionally, redacting the sensitive data from the prompts and replies.
5. Securely logging the interactions between the user, the GenAI application and the LLM model. 

## **Getting Started**

This sample is to meant to work with AWS Bedrock. To get started with the code examples, clone the repository and 
navigate to the paig-quickstart directory and follow the instructions provided here.

### Prerequisites

1. Enable any model from the AWS Bedrock service.
2. AWS STS credentials with the necessary permissions to call the Amazon Bedrock service.
3. Minimum Python version 3.11.5
4. PAIG Server by defaults starts on port 4545. Make sure the port is available.


### Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip3 install -r requirements.txt
```

### Download Spacy Model
```bash
python3 -m spacy download en_core_web_lg
```
### Start PAIG Server in the background
```bash
paig run &
```

```bash
python3 app.py
```