# Elasticsearch MCP Server

## About

Elasticsearch MCP Server is a natural language interface to Elasticsearch data using the Model Context Protocol (MCP). The system allows users to query Elasticsearch indices using conversational language rather than complex query syntax. When combined with other MCP servers like a Weather API, it enables powerful multi-domain AI applications that can connect information across different data sources.

MCP serves as a standardized protocol for Agentic AI communication, much like TCP/IP does for network communication. It creates a well-defined interface that enables LLMs to interact with external tools and data sources through a consistent, structured approach. This standardization is particularly valuable in the emerging field of Agentic AI, where autonomous AI systems need reliable ways to access, process, and act upon information from diverse sources.

By implementing the Model Context Protocol, this project demonstrates how Agentic AI systems can:

1. Maintain clear separation of responsibilities - The agent (LLM) focuses on reasoning and planning, while specialized tools handle data retrieval and domain-specific operations
2. Seamlessly communicate with vector stores like Elasticsearch for semantic search and information retrieval
3. Integrate with external APIs like weather services without requiring custom code for each integration
4. Provide more accurate and comprehensive responses by incorporating real-time data and domain-specific knowledge beyond what's in the model's training data
5. Build complex, multi-step reasoning chains that span multiple tools and information sources

This architecture creates a flexible foundation for Agentic AI systems that can be extended to encompass additional data sources, APIs, and tools without changing the underlying protocol. Just as TCP/IP enabled diverse applications to communicate over a common network infrastructure, MCP enables diverse AI agents and tools to work together through a common interaction protocol, accelerating development of increasingly sophisticated AI applications.





## Components

1. **Elasticsearch MCP Server**: Provides natural language access to Elasticsearch indices
Tools:
    - search_elasticsearch: Dynamically searches Elasticsearch indices based on natural language queries
        Parameters: query (string), top_k (integer, optional)
        Features: Automatically handles nested fields, adapts to index structure, supports fuzzy matching
        Returns: Formatted search results with relevant document content
    - get_index_info: Retrieves metadata about available indices or a specific index
        Parameters: index_name (string, optional)
        Features: Shows document count, size, and field structure including nested fields
        Returns: Detailed information about index structure and statistics

2. **Weather MCP Server** : Provides weather forecast data via the NWS API

Tools:
    - get_forecast: Retrieves detailed weather forecast for a specific location
        Parameters: latitude (float), longitude (float)
        Features: Multi-day forecast, temperature data, wind conditions, precipitation details
        Returns: Formatted forecast broken down by time periods (today, tonight, tomorrow, etc.)
    - get_alerts: Retrieves active weather alerts for a specified US state
        Parameters: state (string) - two-letter US state code
        Features: Emergency alerts, severe weather warnings, hazard notifications
        Returns: Formatted alert information including severity, description, and instructions

3. **Multi-Server MCP Client**: Integrates multiple MCP servers with Amazon Bedrock

Key Functions:
    - Tool Discovery: Automatically discovers and registers all available tools from connected servers
    - Tool Routing: Routes tool calls to the appropriate servers based on tool names
    - Conversation Management: Maintains context across multiple tool calls and servers
    - Response Synthesis: Uses Claude to integrate results from multiple tools into coherent responses
    - Error Handling: Gracefully handles failures in tool execution and server communication


### Workflow

1. User submits a natural language query to the MCP client
2. Client forwards query to a foundation model in Amazon Bedrock
3. Foundation model  analyzes the query and determines which tools to use
4. Tool calls are routed to the appropriate MCP server (ES and/or Weather)
5. Results are returned to foundation model for final response synthesis
6. User receives a comprehensive answer that may combine data from multiple sources

## Setup Instructions

### Prerequisites

- Python 3.8+ with uv package manager
- Access to Amazon Bedrock with Anthropic's Claude (or your choice of foundation model) model enabled
- Access to Elasticsearch cloud or serverless
- AWS account with proper IAM permissions for Bedrock

### 1. Install Dependencies

```bash

# install uv
cd mcp
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a new environment
uv venv

# Activate the environment
source .venv/bin/activate  # On Unix/Mac
# or
.\.venv\Scripts\activate   # On Windows

# Install required packages
uv pip install elasticsearch[async]>=8.0.0 aiohttp httpx mcp[cli] boto3
```

### 2. Configure Elasticsearch

Set up your Elasticsearch index with customer data:

```
# In Elasticsearch Dev Tools console

# Create the customers index
PUT customers
{
  "mappings": {
    "properties": {
      "name": { "type": "text" },
      "email": { "type": "keyword" },
      "phone": { "type": "keyword" },
      "address": { "type": "text" },
      "join_date": { "type": "date" },
      "membership_level": { "type": "keyword" },
      "purchase_history": {
        "type": "nested",
        "properties": {
          "date": { "type": "date" },
          "product_id": { "type": "keyword" },
          "product_name": { "type": "text" },
          "amount": { "type": "float" }
        }
      }
    }
  }
}

# Add the first customer
POST customers/_doc/1
{
  "name": "John Doe",
  "email": "john.doe@example.com",
  "phone": "555-123-4567",
  "address": "123 Main St, New York, NY 10001",
  "join_date": "2021-03-15",
  "membership_level": "gold",
  "purchase_history": [
    {
      "date": "2022-01-10",
      "product_id": "P001",
      "product_name": "Smartphone",
      "amount": 899.99
    },
    {
      "date": "2022-02-15",
      "product_id": "P002",
      "product_name": "Wireless Headphones",
      "amount": 199.99
    }
  ]
}

# Add the second customer
POST customers/_doc/2
{
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "phone": "555-987-6543",
  "address": "456 Park Ave, San Francisco, CA 94108",
  "join_date": "2022-05-20",
  "membership_level": "silver",
  "purchase_history": [
    {
      "date": "2022-06-05",
      "product_id": "P003",
      "product_name": "Laptop",
      "amount": 1299.99
    },
    {
      "date": "2022-07-12",
      "product_id": "P004",
      "product_name": "External Hard Drive",
      "amount": 129.99
    }
  ]
}
```


### 5. Configure AWS Credentials

Set up AWS credentials for Bedrock access:

```bash
# Set environment variables (temporary)
export AWS_ACCESS_KEY_ID=your_access_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_access_key
export AWS_REGION=us-east-1

# Or configure AWS CLI (permanent)
aws configure
```

Update Elasticsearch credentials in elasticsearch_retriever.py:

```bash
# Elasticsearch configuration
ES_CLOUD_ID = ""
ES_API_KEY = "
```

## Running the Multi-Server MCP Client

### Start Both Servers and the Client

1. Run the client with both server scripts:

```bash
uv run multi_server_client.py /path/to/weather.py /path/to/elastic_retriever.py
```

### Sample Prompt

Once the client is running, you can enter the following prompt:

```
Find out city where John Doe is located from his purchase history and then get me a summary of the weather forecast for this city
```

### Expected Workflow

1. The client will send the prompt to Claude
2. Claude will identify this as a multi-step task:
   - First, search Elasticsearch for John Doe's location
   - Then, get the weather forecast for that location
3. Claude will call the `search_elasticsearch` tool with an appropriate query
4. After receiving the address information (New York), Claude will parse the city and state
5. Claude will then call the `get_forecast` tool with the coordinates for New York
6. Finally, Claude will provide a summary of the weather forecast for New York

### Example Response

```
I found that John Doe is located in New York, NY based on his customer information. The address listed is 123 Main St, New York, NY 10001.

Here's the weather forecast for New York:

TODAY:
Temperature: 75°F
Wind: 10 mph NW
Forecast: Partly sunny with a chance of afternoon showers. Humidity around 65%.

TONIGHT:
Temperature: 62°F
Wind: 5 mph NW
Forecast: Mostly clear with temperatures dropping to the low 60s. Perfect evening for outdoor activities.

THURSDAY:
Temperature: 78°F
Wind: 8 mph SW
Forecast: Sunny with increasing clouds later in the day. No precipitation expected.

THURSDAY NIGHT:
Temperature: 64°F
Wind: 6 mph SW
Forecast: Partly cloudy with comfortable temperatures.

FRIDAY:
Temperature: 80°F
Wind: 12 mph S
Forecast: Warm and humid with a 30% chance of thunderstorms in the late afternoon.

In summary, the next few days in New York where John Doe lives will be mostly pleasant with mild temperatures and only a slight chance of showers today and thunderstorms on Friday.
```

## Conclusion

This project demonstrates how to create MCP-compliant servers for data retrieval and integrate them with foundation models to provide seamless responses to complex queries that span multiple domains of information.