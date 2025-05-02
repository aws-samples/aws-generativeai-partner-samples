import asyncio
import sys
from typing import Dict, List, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# to interact with Amazon Bedrock
import boto3

# Constants
MAX_TOKENS = 2000
MAX_TURNS = 15


SYSTEM_PROMPT = """
You are an advanced financial analysis AI with access to real-time market data through the Confluent MCP server and historical data through the Elastic MCP server. Your task is to provide comprehensive insights by combining streaming and historical data.

To answer the user's query, follow these steps:

1. Analyze the query to determine required data types:
   - Real-time data needs (e.g., current prices, live order books). For this go to Confluent Server.
   - Historical data needs (e.g., past performance, long-term trends). For this got to Elasticsearch Server.

2. Formulate queries for the Confluent MCP server:
   - For real-time market data, go to the Confluent Server Topics with names "market_data", "order_book" and "trades" only. No need to check for other topics.
   - Example: "Get current order book for AMZN", go to "order_book" topic in Confluent.
   - For the Flink SQL statements always assume that the default catalog name is "default". In other words, sql.current-catalog="default".
   - Similarly for all of the Flink SQL statements, always assume that the default database is "cluster_0". In other words,sql.current-database="cluster_0". 
   - Do not execute unnessarily same Flink SQL statement many times and unnessarily increase input token size and get in to error like: "Input is too long for requested model." Avoid this situation.
   - Every Flink SQL statement should have LIMIT parameter set to any value between 1 to 5 and after first execution and results fetched, immediately stop executing the Flink SQL statement.
   - Example: Here is an example "order_book" topic structure looks like:
   	 For key = AMZN
   	 Value = {"event_type": "order-book","symbol": "AMZN","stampedtime": "2025-04-23T23:00:12.609157","bids": [ {"price": 366.82,"quantity": 1661},{"price": 366.45,"quantity": 4527},],"asks": [{"price": 366.82,"quantity": 3606},{"price": 367.19,"quantity": 205}]}
   - Example: Here is an example "markdet_data" topic structure looks like:
   	 For key = AMZN
   	 Value = {"event_type": "market-data","symbol": "AMZN","stampedtime": "2025-04-23T23:00:12.609086","price": 362.71, "volume": 815,"bid": 362.7,"ask": 362.72,"exchange": "LSE","volatility": 1.1199094504889437}
   - Example: Here is an example data for "trades"
   	 For key = AMZN
   	 Value = {  "event_type": "trade",  "trade_id": "ce9e4c10-943d-4784-b131-eabfc9f82286",  "symbol": "AMZN",  "stampedtime": "2025-04-23T23:00:12.609122",  "price": 368.95,  "quantity": 792,  "side": "sell",  "order_type": "market",  "trader_id": "e88bba69-24e1-4729-91e5-14c5069c15a9",  "execution_venue": "TSE"}

3. Formulate queries for the Elastic MCP server:
   - For historical data, use only Elasticsearch indices with the names: "market-data" and "trading-metrics"
   - Here are the mappings for "market-data" index.
   {  "mappings": {    "properties": {      "adjusted-close": {        "type": "float"      },      "close": {        "type": "float"      },      "exchange": {        "type": "keyword"      },      "high": {        "type": "float"      },      "low": {        "type": "float"      },      "open": {        "type": "float"      },      "price": {        "type": "float"      },      "symbol": {        "type": "keyword"      },      "timestamp": {        "type": "date"      },      "volume": {        "type": "long"      }    }  }}
   
   - Here are the mappings for "trading-metrics"
   {  "mappings": {    "properties": {      "ma-20": {        "type": "float"      },      "ma-50": {        "type": "float"      },      "rsi": {        "type": "float"      },      "symbol": {        "type": "keyword"      },      "timestamp": {        "type": "date"      },      "volatility": {        "type": "float"      },      "volume-ma": {        "type": "float"      }    }  }}

4. Integrate data from both sources:
   - Compare real-time patterns with historical trends
   - Identify anomalies or significant deviations

5. Apply financial analysis techniques:
   - Utilize appropriate models (e.g., time series analysis, risk metrics)
   - Consider market conditions and relevant external factors

6. Generate insights and recommendations:
   - Synthesize findings into clear, actionable advice
   - Provide confidence levels and potential risks

7. Format the response:
   - Present key points first, followed by supporting details
   - Include relevant visualizations or metrics when appropriate

Remember to maintain data privacy and adhere to financial regulations in your analysis and recommendations.

Now, based on the user's query, proceed with your analysis and provide a comprehensive response.
"""

@dataclass
class Message:
    role: str
    content: List[Dict[str, Any]]

    @classmethod
    def user(cls, text: str) -> 'Message':
        return cls(role="user", content=[{"text": text}])

    @classmethod
    def assistant(cls, text: str) -> 'Message':
        return cls(role="assistant", content=[{"text": text}])

    @classmethod
    def tool_result(cls, tool_use_id: str, content: List[Dict]) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": content
                }
            }]
        )

    @classmethod
    def tool_request(cls, tool_use_id: str, name: str, input_data: dict) -> 'Message':
        return cls(
            role="assistant",
            content=[{
                "toolUse": {
                    "toolUseId": tool_use_id,
                    "name": name,
                    "input": input_data
                }
            }]
        )

    @staticmethod
    def to_bedrock_format(tools_list: List[Dict]) -> List[Dict]:
        return [{
            "toolSpec": {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": tool["input_schema"]["properties"],
                        "required": tool["input_schema"].get("required", [])
                    }
                }
            }
        } for tool in tools_list]
    
class MultiServerMCPClient:
    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-west-2')
        self.all_tools = {}
        self.server_configs = {}

    async def connect_to_servers(self, server_configs: Dict[str, Dict]):
        """Connect to multiple MCP servers"""
        self.server_configs = server_configs
        for server_name, config in server_configs.items():
            await self.connect_to_server(server_name, config)
        
        print(f"\nConnected to {len(self.sessions)} servers with {len(self.all_tools)} total tools")
        for server, tools in self.all_tools.items():
            print(f"- {server}: {[tool.name for tool in tools]}")

    async def connect_to_server(self, server_name: str, config: Dict):
        """Connect to an MCP server using the provided configuration"""
        if "command" not in config:
            raise ValueError(f"Invalid server configuration for {server_name}: missing 'command'")

        server_params = StdioServerParameters(
            command=config["command"],
            args=config.get("args", []),
            env=config.get("env", None)
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        response = await session.list_tools()
        print(f"\nConnected to {server_name} with tools:", [tool.name for tool in response.tools])
        
        self.sessions[server_name] = session
        self.all_tools[server_name] = response.tools

    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={
                "maxTokens": MAX_TOKENS,
                "temperature": 0.7,
                "topP": 0.9,
            },
            toolConfig={"tools": tools}
        )

    async def process_query(self, query: str) -> str:
        messages = [
            Message.user(SYSTEM_PROMPT).__dict__,
            Message.user(query).__dict__
        ]
        
        available_tools = []
        for server_name, tools in self.all_tools.items():
            for tool in tools:
                tool_info = {
                    "name": f"{tool.name}",
                    "server": server_name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                
                if "required" not in tool_info["input_schema"]:
                    tool_info["input_schema"]["required"] = []
                    if tool_info["input_schema"]["properties"]:
                        first_param = next(iter(tool_info["input_schema"]["properties"]))
                        tool_info["input_schema"]["required"] = [first_param]
                
                available_tools.append(tool_info)

        bedrock_tools = Message.to_bedrock_format(available_tools)
        response = self._make_bedrock_request(messages, bedrock_tools)
        
        return await self._process_response(response, messages, bedrock_tools, available_tools)

    async def _process_response(
        self, 
        response: Dict, 
        messages: List[Dict], 
        bedrock_tools: List[Dict],
        available_tools: List[Dict]
    ) -> str:
        final_text = []
        turn_count = 0
        tool_to_server = {tool["name"]: tool["server"] for tool in available_tools}
        
        try:
            while turn_count < MAX_TURNS:
                if response['stopReason'] == 'tool_use':
                    for item in response['output']['message']['content']:
                        if 'text' in item:
                            thinking_text = item['text']
                            final_text.append(f"[Thinking: {thinking_text}]")
                        
                        elif 'toolUse' in item:
                            tool_info = item['toolUse']
                            tool_name = tool_info['name']
                            
                            server_name = tool_to_server.get(tool_name)
                            if not server_name:
                                error_msg = f"Tool {tool_name} not found in any connected server"
                                final_text.append(f"[ERROR: {error_msg}]")
                                return "\n".join(final_text)
                            
                            tool_result, messages = await self._handle_tool_call(
                                server_name, 
                                tool_info, 
                                messages
                            )
                            final_text.extend(tool_result)
                            
                            response = self._make_bedrock_request(messages, bedrock_tools)
                            turn_count += 1
                            break
                    
                else:  # For non-tool_use responses
                    if 'output' in response and 'message' in response['output']:
                        response_text = response['output']['message']['content'][0]['text']
                        final_text.append(response_text)
                    return "\n".join(final_text)

            if turn_count >= MAX_TURNS:
                final_text.append("\n[Maximum conversation turns reached.]")
                
            return "\n".join(final_text)
            
        except Exception as e:
            import traceback
            final_text.append(f"\n[Error processing response: {str(e)}]")
            final_text.append(traceback.format_exc())
            return "\n".join(final_text)

    async def _handle_tool_call(
        self, 
        server_name: str, 
        tool_info: Dict, 
        messages: List[Dict]
    ) -> tuple[List[str], List[Dict]]:
        """Handle a tool call and return the results and updated messages"""
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        session = self.sessions[server_name]
        result = await session.call_tool(tool_name, tool_args)

        tool_result_content = [{"json": {"text": content.text}} for content in result.content if content.text]

        tool_request = Message.tool_request(tool_use_id, tool_name, tool_args)
        tool_result = Message.tool_result(tool_use_id, tool_result_content)
        
        messages.append(tool_request.__dict__)
        messages.append(tool_result.__dict__)
        
        formatted_result = [
            f"[Calling tool {tool_name} on server {server_name} with args {tool_args}]",
            f"[Tool {tool_name} returned: {result.content[0].text if result.content else 'No content'}]"
        ]
        
        return formatted_result, messages

    async def chat_loop(self):
        print("\nWelcome to the Multi-Server MCP Chat featuring the best of Confluent and Elasticsearch!")
        print("Type 'quit' to exit or your query.")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                if query.lower() == 'quit':
                    break
                
                print("\nAssistant:", end=" ")
                response = await self.process_query(query)
                print(response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()

    async def cleanup(self):
        await self.exit_stack.aclose()

async def main():
    load_dotenv()
    es_url = os.getenv("ES_URL")
    es_api_key = os.getenv("ES_API_KEY")
    mcp_app_env_path = os.getenv("MCP_APP_ENV_PATH", "/home/ec2-user/aws-generativeai-partner-samples/elastic/mcp/multi-mcpserver-elastic-confluent-fintech/.env")

    if not es_url or not es_api_key:
        print("Error: ES_URL and ES_API_KEY must be set in the .env file")
        sys.exit(1)

    server_configs = {
        "confluent": {
            "command": "npx",
            "args": ["-y", "@confluentinc/mcp-confluent", "-e", mcp_app_env_path]
        },
        "elasticsearch-mcp-server": {
            "command": "npx",
            "args": ["-y", "@elastic/mcp-server-elasticsearch"],
            "env": {
                "ES_URL": es_url,
                "ES_API_KEY": es_api_key
            }
        }
    }

    client = MultiServerMCPClient()
    try:
        await client.connect_to_servers(server_configs)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())