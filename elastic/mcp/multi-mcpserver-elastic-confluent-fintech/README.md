# Multi-Server MCP based Financial Analytics Application

This application demonstrates the integration of Confluent and Elasticsearch Model Completion Protocol (MCP) servers to create a powerful financial analytics platform. The application leverages real-time streaming data from **Confluent** and historical data from **Elasticsearch** to provide comprehensive financial insights leveraging **Amazon Bedrock** LLMs.

## Overview

The Multi-Server MCP Financial Analytics Application combines:

- **Real-time market data** from Confluent Kafka streams
- **Historical financial data** from Elasticsearch indices
- **Claude 3.5 Sonnet** AI model via **Amazon Bedrock** for intelligent analysis

This integration enables advanced financial analytics by combining streaming and historical data sources, allowing users to query both real-time market conditions and historical trends through a unified interface.

## Architecture

The application consists of the following components:

1. **Confluent MCP Server**: Provides access to real-time market data, order books, and trade information through Kafka topics
2. **Elasticsearch MCP Server**: Provides access to historical market data and trading metrics
3. **Multi-Server MCP Client**: Connects to both servers and coordinates interactions with the Claude AI model
4. **Data Loaders**: Utilities to populate Kafka topics and Elasticsearch indices with sample data
```

                   ┌─────────────────────┐
                   │    LLM User Query   │
                   │ "What's the current │
                   │  AMZN trend vs      │
                   │  historical pattern?"│
                   └──────────┬──────────┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │  Multi-server MCP Client    │
              └─────────────┬───────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
              ▼             ▼             ▼
┌─────────────────┐ ┌───────────────┐ ┌───────────────┐
│  Confluent MCP  │ │ Elasticsearch │ │ Amazon Bedrock │
│     Server      │ │   MCP Server  │ │  (Claude 3.5)  │
└────────┬────────┘ └───────┬───────┘ └───────┬───────┘
         │                  │                 │
         ▼                  ▼                 │
┌─────────────────┐ ┌───────────────┐         │
│ Confluent Kafka │ │ Elasticsearch │         │
│ + Apache Flink  │ │(Historical data)        │
│(Real-time Stream│ └───────────────┘         │
│  Processing)    │         │                 │
└────────┬────────┘         │                 │
         │                  │                 │
         └──────────┬───────┘                 │
                    │                         │
                    └─────────────────────────┘
                              │
                              ▼
                   ┌─────────────────────┐
                   │    LLM Response     │
                   │"AMZN shows bullish  │
                   │pattern with 15% vol │
                   │increase vs history" │
                   └─────────────────────┘
```

### Flow
- Users ask questions in natural language
- Data is gathered from multiple sources (Elastic for long-term historical data and Confluent for real-time streaming data) through MCP servers
- Gathered data is fed to LLM
- The LLM generates a comprehensive, natural language response
- The response combines real-time insights with historical context


## Prerequisites

- Python 3.10+
- Node.js and npm
- AWS account with access to Amazon Bedrock
- Confluent Cloud account
- Elasticsearch Cloud account

## Setup Instructions

### 1. Spin up EC2 and prep
Spin up an EC2 machine with the followsing instance type details:
- Amazon Linux 2023 AMI
- 64-bit (x86)
- t2.medium
- 40GB gp3 storage

After you launch EC2 machine,  install git and clone this repo.

```bash
sudo yum install git -y
sudo yum install nodejs -y

git clone https://github.com/aws-samples/aws-generativeai-partner-samples.git
cd elastic/mcp/multi-mcpserver-elastic-confluent-fintech/
```


### 2. Install Dependencies
If you are not running Python3.10+, here is how you can upgrade for Amazon Linux as an example:

```bash
sudo dnf upgrade --releasever=2023.7.20250331
# Search for python3.XX versions. 
sudo yum list available | grep python3

# if Python 3.10 or 3.11 is found, simply install.
sudo yum install python3.11
python3.11 --version
sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo alternatives --config python3
python3 --version
```

### 3. Elasticsearch Setup

Setup Elastic Cloud on AWS using the free trial [here](https://cloud.elastic.co/registration?fromURI=%2Fhome).
Note the following details to connect to Elastic Cloud from your application.

- Elasticsearch deployment (cloud or local)
- Elasticsearch API key
- In the next step (not now) you will create .env file. Please make a note of the following credentials that you will use in the next step :
```    
        ES_URL=your-elasticsearch-url 
        ES_API_KEY=your-api-key
```

### 4. Confluent Kafka Cluster Setup

Sign up for Confluent free trial account [here](https://www.confluent.io/get-started/).
Create a Kafka cluster.

### 5. Set Up Environment Variables

Run the script `environment_variables_setup.sh` to setup `.env` file with the following credentials:
- Confluent Cloud credentials
- Elasticsearch credentials
- AWS credentials (for Bedrock access)

Make the script executable by adding execute permissions:
```
chmod +x environment_variables_setup.sh
./environment_variables_setup
```

To find the Confluent Kafka related configurations, please refer to [this document](./docs/confluent-configurations.md).
To find the Elastic related configurations, please refer to [this document](./docs/elastic-configurations.md).

### 6. Install more Dependencies

```
# install uv
cd aws-generativeai-partner-samples/elastic/mcp/multi-mcpserver-elastic-confluent-fintech
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new environment
uv venv multi-mcp-env

# Activate the environment
source multi-mcp-env/bin/activate  # On Unix/Mac
# or
.\multi-mcp-env\Scripts\activate   # On Windows

# Install required packages
uv pip install -r requirements.txt

# Install MCP server packages
npm install -g @confluentinc/mcp-confluent
```

### 7. Load Sample Data

#### Load data into Elasticsearch:

```bash
cd data-loader
python elasticsearch_historical_loader.py
```

#### Start the Kafka data simulator:

```bash
cd data-loader
python confluent_kafka_trading_data_simulator.py
```

## Running the Application

### 1. Start the MCP Client

```bash
cd mcp-clients
python multi-server-confluent-elastic-fintech-client.py
```

The client will:
1. Connect to both the Confluent and Elasticsearch MCP servers
2. Initialize a chat interface for interacting with the AI
3. Process user queries by coordinating between the AI model and the MCP servers

### 2. Interact with the Application

Once the application is running, you can enter financial analysis queries such as:

- "What can you do for me? Give me a few examples of questions I can ask."
- "Based on currrent market conditions and historical patterns for the last 1 month, what's the optimal entry point for NVDA?"
- "What's the current order book for AMZN?"
- "Show me the volatility trend for TSLA over the past month"
- "Identify any anomalies in today's trading volume for MSFT compared to historical patterns"

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ES_URL` | Elasticsearch endpoint URL | Yes |
| `ES_API_KEY` | Elasticsearch API key | Yes |
| `CONFLUENT_ENV_PATH` | Path to Confluent environment file | No (defaults to `/home/ec2-user/mcp-financial-analytics/mcp-clients/.env`) |
| `BOOTSTRAP_SERVERS` | Confluent Kafka bootstrap servers | Yes |
| `KAFKA_API_KEY` | Confluent Kafka API key | Yes |
| `KAFKA_API_SECRET` | Confluent Kafka API secret | Yes |
| Various Flink variables | Required for SQL queries on streaming data | Yes |

## Data Schemas

The application works with the following data structures:

### Kafka Topics
- `market_data`: Real-time market data including price, volume, bid/ask
- `order_book`: Order book snapshots with bids and asks
- `trades`: Individual trade execution details

### Elasticsearch Indices
- `market-data`: Historical market data including OHLC prices
- `trading-metrics`: Calculated metrics like moving averages, RSI, and volatility

## Troubleshooting

### Common Issues

1. **Connection Errors**:
   - Verify your Confluent and Elasticsearch credentials in the `.env` file
   - Check network connectivity to the cloud services

2. **MCP Server Errors**:
   - Ensure the npm packages are installed globally
   - Check that the required Node.js version is installed

3. **Bedrock Access Issues**:
   - Verify your AWS credentials and region settings
   - Ensure you have access to the Claude model in Amazon Bedrock