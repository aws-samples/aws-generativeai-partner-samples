import asyncio
import sys
import os
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands.models import BedrockModel
from mcp import stdio_client, StdioServerParameters
async def main():
    # Initialize TiDB MCP client
    tidb_mcp_client =  MCPClient(
        lambda:stdio_client(
        StdioServerParameters(
            command="uvx",
            args=["--from", "pytidb[mcp]", "tidb-mcp-server"],
            env={
                "TIDB_HOST": os.getenv("TIDB_HOST", "gateway01.us-west-2.prod.aws.tidbcloud.com"),
                "TIDB_PORT": os.getenv("TIDB_PORT", "4000"),
                "TIDB_USERNAME": os.getenv("TIDB_USERNAME", "xxx.root"),
                "TIDB_PASSWORD": os.getenv("TIDB_PASSWORD", "yyyy"),
                "TIDB_DATABASE": os.getenv("TIDB_DATABASE", "test")
           }
            )
        )
    )
    try:
        with tidb_mcp_client:
            # Create agent with TiDB MCP client and Bedrock model
            agent = Agent(
                tools=tidb_mcp_client.list_tools_sync(),
                model=BedrockModel(model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0")
            )
            print("Connected to TiDB via Strands SDK MCP")
            
            # Test queries
            response = agent("Show me all tables in the database")
            print(f"Response: {response}")
            #response = agent("Can you list top 10 items of each table in database")
            #print(f"Test: {response}")
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
if __name__ == "__main__":
    asyncio.run(main())