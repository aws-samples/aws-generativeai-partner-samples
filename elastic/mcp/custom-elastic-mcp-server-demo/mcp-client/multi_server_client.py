import asyncio
import sys
from typing import Dict, List, Optional, Any
from contextlib import AsyncExitStack
from dataclasses import dataclass

# to interact with MCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# to interact with Amazon Bedrock
import boto3

# client.py
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
    def tool_result(cls, tool_use_id: str, content: dict) -> 'Message':
        return cls(
            role="user",
            content=[{
                "toolResult": {
                    "toolUseId": tool_use_id,
                    "content": [{"json": {"text": content[0].text}}]
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
                        "required": tool["input_schema"].get("required", [])  # Handle missing required field
                    }
                }
            }
        } for tool in tools_list]
    

class MultiServerMCPClient:
    MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
        self.all_tools = {}
        self.server_paths = {}

    async def connect_to_servers(self, server_configs: Dict[str, str]):
        """Connect to multiple MCP servers
        
        Args:
            server_configs: Dict mapping server name to script path
        """
        self.server_paths = server_configs
        for server_name, script_path in server_configs.items():
            await self.connect_to_server(server_name, script_path)
        
        print(f"\nConnected to {len(self.sessions)} servers with {len(self.all_tools)} total tools")
        for server, tools in self.all_tools.items():
            print(f"- {server}: {[tool.name for tool in tools]}")

    async def connect_to_server(self, server_name: str, server_script_path: str):
        if not server_script_path.endswith(('.py', '.js')):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if server_script_path.endswith('.py') else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        stdio, write = stdio_transport
        session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
        await session.initialize()

        response = await session.list_tools()
        print(f"\nConnected to {server_name} with tools:", [tool.name for tool in response.tools])
        
        # Store the session and tools
        self.sessions[server_name] = session
        self.all_tools[server_name] = response.tools

    async def cleanup(self):
        await self.exit_stack.aclose()
    
    def _make_bedrock_request(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        return self.bedrock.converse(
            modelId=self.MODEL_ID,
            messages=messages,
            inferenceConfig={"maxTokens": 1000, "temperature": 0},
            toolConfig={"tools": tools}
        )

    async def process_query(self, query: str) -> str:
        # Prepare the messages
        messages = [Message.user(query).__dict__]
        
        # Collect all tools from all servers
        available_tools = []
        for server_name, tools in self.all_tools.items():
            for tool in tools:
                # Add server name prefix to tool name for tracking
                tool_info = {
                    "name": f"{tool.name}",  # Keep original name for the LLM
                    "server": server_name,   # Track which server owns this tool
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                
                # Fix missing 'required' field if needed
                if "required" not in tool_info["input_schema"]:
                    tool_info["input_schema"]["required"] = []
                    # Assume first parameter is required for tools with parameters
                    if tool_info["input_schema"]["properties"]:
                        first_param = next(iter(tool_info["input_schema"]["properties"]))
                        tool_info["input_schema"]["required"] = [first_param]
                
                available_tools.append(tool_info)

        # Convert to Bedrock format
        bedrock_tools = Message.to_bedrock_format(available_tools)

        # Send request to Bedrock
        response = self._make_bedrock_request(messages, bedrock_tools)

        # Process the response
        return await self._process_response(response, messages, bedrock_tools, available_tools)
    

    async def _process_response(
        self, 
        response: Dict, 
        messages: List[Dict], 
        bedrock_tools: List[Dict],
        available_tools: List[Dict]
    ) -> str:
        final_text = []
        MAX_TURNS = 10
        turn_count = 0

        # Create tool name to server mapping
        tool_to_server = {tool["name"]: tool["server"] for tool in available_tools}

        while True:
            if response['stopReason'] == 'tool_use':
                final_text.append("received toolUse request")
                for item in response['output']['message']['content']:
                    if 'text' in item:
                        final_text.append(f"[Thinking: {item['text']}]")
                        messages.append(Message.assistant(item['text']).__dict__)
                    elif 'toolUse' in item:
                        tool_info = item['toolUse']
                        tool_name = tool_info['name']
                        
                        # Find which server this tool belongs to
                        server_name = tool_to_server.get(tool_name)
                        if not server_name:
                            error_msg = f"Tool {tool_name} not found in any connected server"
                            final_text.append(f"[ERROR: {error_msg}]")
                            break
                        
                        # Call the tool on the appropriate server
                        result = await self._handle_tool_call(server_name, tool_info, messages)
                        final_text.extend(result)
                        
                        response = self._make_bedrock_request(messages, bedrock_tools)
                        
            elif response['stopReason'] == 'max_tokens':
                final_text.append("[Max tokens reached, ending conversation.]")
                break
            elif response['stopReason'] == 'stop_sequence':
                final_text.append("[Stop sequence reached, ending conversation.]")
                break
            elif response['stopReason'] == 'content_filtered':
                final_text.append("[Content filtered, ending conversation.]")
                break
            elif response['stopReason'] == 'end_turn':
                final_text.append(response['output']['message']['content'][0]['text'])
                break

            turn_count += 1

            if turn_count >= MAX_TURNS:
                final_text.append("\n[Max turns reached, ending conversation.]")
                break

        return "\n\n".join(final_text)


    async def _handle_tool_call(self, server_name: str, tool_info: Dict, messages: List[Dict]) -> List[str]:
        tool_name = tool_info['name']
        tool_args = tool_info['input']
        tool_use_id = tool_info['toolUseId']

        # Get the right session for this server
        session = self.sessions[server_name]

        # Call the tool on the appropriate server
        result = await session.call_tool(tool_name, tool_args)

        # Update messages with tool request and result
        messages.append(Message.tool_request(tool_use_id, tool_name, tool_args).__dict__)
        messages.append(Message.tool_result(tool_use_id, result.content).__dict__)

        return [f"[Calling tool {tool_name} on server {server_name} with args {tool_args}]"]

    async def chat_loop(self):
        print("\nMulti-Server MCP Client Started!\nType your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
                response = await self.process_query(query)
                print("\n" + response)
            except Exception as e:
                print(f"\nError: {str(e)}")
                import traceback
                traceback.print_exc()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python multi_server_client.py <weather_server_script> <elasticsearch_server_script>")
        sys.exit(1)

    weather_script = sys.argv[1]
    elasticsearch_script = sys.argv[2]
    
    server_configs = {
        "weather": weather_script,
        "elasticsearch": elasticsearch_script
    }

    client = MultiServerMCPClient()
    try:
        await client.connect_to_servers(server_configs)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())