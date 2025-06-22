# Meta LLaMA 3 on Amazon Bedrock

This sample shows how to use Meta's LLaMA models via Amazon Bedrock for natural language tasks like summarization, Q&A, and PDF interaction, using S3 and SageMaker Studio.

No model hosting required — Bedrock gives instant access to LLaMA 3 via API.

---

## Project Structure

```bash
meta/
├── samples/
│   └── llama3-boto3-pdf-chat.ipynb     # Use LLaMA 3 to chat with PDFs stored in S3
├── README.md                           # This file
```

---

## Prerequisites

- AWS account with access to Amazon Bedrock (region: us-east-1)
- LLaMA 3 access enabled in the Bedrock console (see below)
- S3 bucket created (e.g. llama3-chat-data)
- Python environment with boto3, PyMuPDF (fitz)

---

## Quick Start

### 1. Enable LLaMA 3 access
Go to the Bedrock Console > Model Access: https://console.aws.amazon.com/bedrock/home and enable:
- meta.llama3-8b-instruct-v1:0

### 2. Clone this repo and open the notebook
```bash
git clone https://github.com/YOUR-ORG/aws-generativeai-partner-samples.git
cd aws-generativeai-partner-samples/meta/samples
```

### 3. Upload a sample PDF to S3
```bash
aws s3 cp sample.pdf s3://llama3-chat-data/uploads/sample.pdf
```

### 4. Run the notebook
Launch SageMaker Studio, open `llama3-boto3-pdf-chat.ipynb`, and run through the cells.

---

## Model Parameters

You can adjust the following generation parameters in the Bedrock payload:

| Parameter       | Description                           | Example       |
|----------------|---------------------------------------|---------------|
| temperature    | Controls randomness                   | 0.3–1.0       |
| top_p          | Limits token pool                     | 0.85–0.95     |
| max_gen_len    | Max tokens to generate                | 512           |
| stop_sequences | Strings to stop generation            | ["\nUser:"]    |

---

## Notes
- This example uses LLaMA 3 8B Instruct (meta.llama3-8b-instruct-v1:0) via Bedrock.
- Works in us-east-1 (required region for Meta models).
- You can extend this to chunk large PDFs, add chat history, or stream outputs.

---

## License
Apache 2.0
