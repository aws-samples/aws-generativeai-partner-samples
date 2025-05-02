# Amazon Bedrock with Elastic - Agentic workflows with official Elastic MCP Server Demo

## Travel & Tourism Industry Analytics powered by Amazon Bedrock and Elastic MCP Server

This application demonstrates an intelligent analytics system for the hospitality industry, combining the power of Amazon Bedrock's Large Language Models with Elasticsearch's real-time search and analytics capabilities through Model-Content-Protocol (MCP) servers.

## Overview 

The application provides intelligent analysis of weather impacts on hotel operations, revenue, and guest satisfaction by leveraging: 
- Amazon Bedrock's Claude 3 Sonnet for natural language understanding and reasoning 
- Elasticsearch's official MCP server for efficient data querying and analytics 
- Custom Weather MCP server for real-time weather data 
- Multi-server architecture for scalable and modular functionality 

                                 ┌────────────────────────┐
                                 │  Amazon Bedrock 	  │
                                 │  (Claude Sonnet 3)     │
                                 └────────┬───────────────┘
                                          │
                              ┌───────────┴──────────┐
                              │                      │
                     ┌────────┴───────┐    ┌─────────┴────────┐
                     │ Weather MCP    │    │ Elastic MCP      │
                     │ Server         │    │ Server           │
                     └────────────────┘    └───────┬──────────┘
                                                   │
                                          ┌────────┴────────┐
                                          │  Elasticsearch  │
                                          └─────────────────┘

### Key Features 
- Natural language queries for complex hotel analytics 
- Real-time weather impact analysis 
- Cross-referenced data analysis across multiple domains: 
	- Hotel operations 
	- Booking patterns 
	- Event management 
	- Revenue metrics 
	- Weather patterns 
	- Intelligent recommendations for weather-related business decisions

## Setup

### AWS Account Setup
- Active AWS account with access to Amazon Bedrock 
- AWS CLI installed and configured 
- Permissions to use Claude 3 Sonnet model
- Set up AWS credentials for Bedrock access:

```shell
# Set environment variables (temporary)
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=us-east-1

# Or configure AWS CLI (permanent)
aws configure
```

### Elasticsearch Setup

- Elasticsearch deployment (cloud or local)
- Elasticsearch API key
- Create .env file with credentials:
    
        ES_URL=your-elasticsearch-url 
        ES_API_KEY=your-api-key`

### Install Dependencies
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


```bash
git clone [this-repository-url]
# install uv
cd aws-generativeai-partner-samples/elastic/mcp/official-elastic-mcp-server-demo
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new environment
uv venv elastic-mcp-official-env

# Activate the environment
source elastic-mcp-official-env/bin/activate  # On Unix/Mac
# or
.\elastic-mcp-official-env\Scripts\activate   # On Windows

# Install required packages
uv pip install -r requirements.txt
```

### Data Loading
Using Elastic Cloud on AWS web console, navigate to Dev Tools and load the data found in the `data` folder.

## Running the Application
Go ahead and run the application. You are supplying the weather MCP server path as an argument. There is no need to run Elasticsearch MCP server locally as you are directly using the official MCP server.

```bash
cd mcp-clients
python multi_server_client_travel_analytics.py ../mcp-servers/weather/weather.py
```

#### Sample Queries to ask

```
When did Summer Beach Music Festival event happened and how is the weather currently there?
```

```
I am planning to stay at Mountain View Lodge. What amenities it has? How is the weather and can I take advantage of these facilities?
```

```
Where is Desert Stargazing Night event happening? And how is the weather there?
```

```
I am going for City Business Innovation Summit. What are the nearest hotels there? How is the weather conditions this week?
```

##  Data Model
The application uses five primary Elasticsearch indices:

1. `hotels`: Basic hotel information and facilities
2. `bookings`: Reservation and guest satisfaction data
3. `events`: Scheduled activities and weather dependencies
4. `revenue_metrics`: Financial and occupancy data
5. `weather_impact_analysis`: Detailed weather effect analysis

## Conclusion
This project demonstrates how to create MCP-compliant servers for data retrieval and integrate them with foundation models to provide seamless responses to complex queries that span multiple domains of information.
### Amazon Bedrock

- Powerful natural language understanding with FMs from Anthropic via Amazon Bedrock
- No ML infrastructure management required
- Pay-per-use pricing model
- Enhanced reasoning capabilities for complex queries

### Elastic MCP Server

- Official integration with Elasticsearch
- Optimized query performance
- Real-time data analytics
- Secure data access
- Advanced hybrid search capabilities.
