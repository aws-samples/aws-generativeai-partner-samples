import os
import sys
import json
import asyncio
import argparse
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.stdio import stdio_client
from langchain_aws import ChatBedrock
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters

def parse_arguments():
    """Parse command line arguments, falling back to environment variables when available"""
    parser = argparse.ArgumentParser(description='Splunk MCP Demo')
    # Model configuration
    parser.add_argument('--model-id', type=str, 
                    help='Bedrock model ID')    
    args = parser.parse_args()
    return args    
class MCPClient:
        
    def __init__(self, args):
        self.splunk_session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        # Store arguments
        self.args = args            
        
    async def connect_to_servers(self):
        """Connect to both MCP servers"""
        # Connect to monitoring server
        monitoring_params = StdioServerParameters(
            command="uv",
            args=["run", "server/splunk-server.py"],
        )

        monitoring_transport = await self.exit_stack.enter_async_context(stdio_client(monitoring_params))
        monitoring_stdio, monitoring_write = monitoring_transport
        self.splunk_session = await self.exit_stack.enter_async_context(
            ClientSession(monitoring_stdio, monitoring_write)
        )

        # Initialize the monitoring MCP server
        await self.splunk_session.initialize()
        print(f"Connected to the Splunk MCP server")
        
        # Load the tools from splunk MCP server
        self.splunk_tools = await load_mcp_tools(self.splunk_session)
        
        print("Available tools:", [tool.name for tool in self.splunk_tools])

    async def process_query(self, query: str, conversation_history=None) -> str:
        """Process a query using ReAct agent and available tools from both servers"""
        if not self.splunk_session:
            return "Error: Not connected to Splunk MCP server. Please connect first."
        
        # Initialize conversation history if not provided
        if conversation_history is None:
            conversation_history = []
        
        # Combine the system prompts
        combined_system_prompt = f"""
        You are an Splunk AI Assistant Expoert with access to multiple tools.
        """
        
        try:
            # Create a model instance
            model = ChatBedrock(model_id=self.args.model_id)
            
            # Create a ReAct agent with all tools
            agent = create_react_agent(
                model,
                self.splunk_tools
            )
            print(f"Initialized the AWS combined ReAct agent...")
            
            # Format messages including conversation history
            formatted_messages = [
                {"role": "system", "content": combined_system_prompt}
            ]
            
            # Add conversation history
            for message in conversation_history:
                formatted_messages.append(message)
                
            # Add current query
            formatted_messages.append({"role": "user", "content": query})
            
            print(f"Formatted messages prepared")
            
            # Invoke the agent
            response = await agent.ainvoke({"messages": formatted_messages})
            
            # Process the response
            if response and "messages" in response and response["messages"]:
                last_message = response["messages"][-1]
                if isinstance(last_message, dict) and "content" in last_message:
                    # Save this interaction in the conversation history
                    conversation_history.append({"role": "user", "content": query})
                    conversation_history.append({"role": "assistant", "content": last_message["content"]})
                    return last_message["content"], conversation_history
                else:
                    conversation_history.append({"role": "user", "content": query})
                    conversation_history.append({"role": "assistant", "content": str(last_message.content)})
                    return str(last_message.content), conversation_history
            else:
                return "No valid response received", conversation_history
                
        except Exception as e:
            print(f"Error details: {e}")
            import traceback
            traceback.print_exc()
            return f"Error processing query: {str(e)}", conversation_history

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nSplunk MCP Server Demo Started!")
        print("Type your queries or 'quit' to exit.")
        print("\nExample queries you can try:")
        print("- Can you write a SPL and query the AWS CloudTrail data, to get list of top 10 AWS events and summarize the result.")
        print("- Can you write a SPL and query the VPC Flow logs data to get a list of top 10 external IPs with failed access to SSH port")
        print("- Can you write and execute SPL to query AWS CloudTrail data. I need to see which AWS account produces the highest count of non-success error code, and by which AWS service and event. Give me a table of final results and provide your summary.")
       

        # Initialize conversation history
        conversation_history = []

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response, conversation_history = await self.process_query(query, conversation_history)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")
        
    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()        
        
async def main():
    # Parse arguments
    args = parse_arguments()
    
    client = MCPClient(args)
    try:
        await client.connect_to_servers()
        await client.chat_loop()
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())        