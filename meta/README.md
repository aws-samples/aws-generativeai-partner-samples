
# Meta's Llama Models on AWS

This project includes sample notebooks that demonstrate how to use Meta's LLaMA models via Amazon Bedrock for natural language tasks such as question answering and PDF interaction. It leverages Bedrock, S3 and SageMaker Studio for development and execution.

---

## Sample Notebooks

| Notebook             | Description |
|----------------------|-------------|
| [`rag-chatbot.ipynb`](samples/rag-chatbot.ipynb) | Demonstrates how to build a simple RAG (Retrieval-Augmented Generation) chatbot using Meta's LLM via Amazon Bedrock, with documents stored in Amazon S3 and vector embeddings generated using Amazon Titan. Uses **LangChain** for document loading, embedding, and retrieval logic. |
| [`summarize-pdf.ipynb`](samples/summarize-pdf.ipynb) | Shows how to use Meta's Llama 3 model via Amazon Bedrock to summarize content extracted from a PDF document.  |

---

## Quick Start

###  Enable Models' Access
Visit the Bedrock Console > Model Access: https://console.aws.amazon.com/bedrock/home and enable the following model:
- `meta.llama3-8b-instruct-v1:0`

In addition the [`rag-chatbot.ipynb`](samples/rag-chatbot.ipynb) sample also requires the following model access
- `amazon.titan-embed-text-v1`


### Clone the Repository and Open the Notebook
In your SageMaker space clone this repository
```bash
git clone https://github.com/${GITHUB_ACTOR}/${GITHUB_REPOSITORY}.git
cd $(basename ${GITHUB_REPOSITORY})/meta/samples
