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

SYSTEM_PROMPT = """You are an AI assistant for hotel and tourism analytics, using Elasticsearch indices to answer weather-related queries. Use these indices:

1. travel.hotels: Basic hotel info (ID, name, location, amenities)
2. travel.bookings: Reservation data, guest satisfaction
3. travel.events: Scheduled activities, weather dependencies
4. travel.revenue_metrics: Financial data, occupancy rates, weather conditions
5. travel.weather_impact_analysis: Detailed weather effects, business impact

When analyzing:
- Revenue: Start with travel.revenue_metrics, cross-reference travel.weather_impact_analysis
- Weather impact: Use travel.weather_impact_analysis, check travel.revenue_metrics for dates
- Events: Begin with travel.events, link to travel.weather_impact_analysis and travel.revenue_metrics
- Bookings: Use travel.bookings, connect to travel.revenue_metrics and travel.weather_impact_analysis

Always: skip your thought process. Get me the answer straight for the question asked.

Remember to:
1. Identify primary index for the query
2. Use additional indices for comprehensive analysis
3. Consider seasonal and location factors
4. Find patterns across indices
5. Offer data-driven, actionable insights

Provide accurate, structured responses to weather-related hospitality queries."""


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
    MODEL_ID = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
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
        print("\nWelcome to the Multi-Server MCP Chat!")
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
    
    if len(sys.argv) < 2:
        print("Usage: python multi_server_client.py <weather_server_script>")
        sys.exit(1)

    weather_script = sys.argv[1]
    
    es_url = os.getenv("ES_URL")
    es_api_key = os.getenv("ES_API_KEY")

    if not es_url or not es_api_key:
        print("Error: ES_URL and ES_API_KEY must be set in the .env file")
        sys.exit(1)

    server_configs = {
        "weather": {
            "command": "python",
            "args": [weather_script],
            "env": None
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
