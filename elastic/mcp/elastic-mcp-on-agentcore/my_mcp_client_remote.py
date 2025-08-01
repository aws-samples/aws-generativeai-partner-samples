import asyncio
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import httpx

agent_arn = "arn:aws:bedrock-agentcore:us-west-2:{ACCOUNT_ID}:runtime/{hosted_agent_elastic_mcp-XXXXXX}"

class AWSAuth:
    def __init__(self, service='bedrock-agentcore', region='us-west-2'):
        self.session = boto3.Session()
        self.credentials = self.session.get_credentials()
        self.region = region
        self.service = service
        
    def get_auth_headers(self, url, method='POST', body=None):
        request = AWSRequest(method=method, url=url, data=body)
        SigV4Auth(self.credentials, self.service, self.region).add_auth(request)
        return dict(request.headers)

async def test_mcp_endpoint():

    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # Test requests including the search tool call
    test_requests = [
        {"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search",
                "arguments": {
                    "index": "events",
                    "query_body": {
                        "query": {
                            "match": {
                                "name": "paris"
                            }
                        },
                        "size": 5
                    }
                }
            }
        }
    ]
    
    aws_auth = AWSAuth()
    
    async with httpx.AsyncClient() as client:
        for req in test_requests:
            body = json.dumps(req)
            headers = aws_auth.get_auth_headers(mcp_url, body=body)
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json, text/event-stream"
            
            print(f"\n--- Testing {req['method']} (ID: {req['id']}) ---")
            print(f"Request: {json.dumps(req, indent=2)}")
            
            try:
                response = await client.post(mcp_url, headers=headers, content=body)
                print(f"Status: {response.status_code}")
                print(f"Response: {response.text}")
                
                # Try to parse and pretty print the response if it's JSON
                try:
                    if response.text.startswith('data: '):
                        # Handle Server-Sent Events format
                        json_part = response.text[6:]  # Remove 'data: ' prefix
                        response_json = json.loads(json_part)
                        print(f"Parsed Response: {json.dumps(response_json, indent=2)}")
                        
                        # Special handling for search results
                        if req['method'] == 'tools/call' and req['params']['name'] == 'search':
                            print("\n=== ELASTICSEARCH SEARCH RESULTS ===")
                            result = response_json.get('result', {})
                            if 'content' in result:
                                for content_item in result['content']:
                                    if content_item['type'] == 'text':
                                        text = content_item['text']
                                        if text.startswith('[{') and text.endswith('}]'):
                                            # This looks like JSON data, let's parse it
                                            try:
                                                search_results = json.loads(text)
                                                print(f"Found {len(search_results)} result(s):")
                                                for i, event in enumerate(search_results, 1):
                                                    print(f"\n--- Event {i} ---")
                                                    print(f"Name: {event.get('name', 'N/A')}")
                                                    print(f"Type: {event.get('type', 'N/A')}")
                                                    print(f"Description: {event.get('description', 'N/A')}")
                                                    print(f"Venue: {event.get('venue', 'N/A')}")
                                                    print(f"Address: {event.get('address', 'N/A')}")
                                                    print(f"Start Date: {event.get('start_date', 'N/A')}")
                                                    print(f"End Date: {event.get('end_date', 'N/A')}")
                                                    print(f"Price Range: {event.get('price_range', 'N/A')}")
                                                    print(f"Ticket Required: {event.get('ticket_required', 'N/A')}")
                                                    print(f"Booking URL: {event.get('booking_url', 'N/A')}")
                                                    print(f"Location: {event.get('latitude', 'N/A')}, {event.get('longitude', 'N/A')}")
                                            except json.JSONDecodeError:
                                                print(f"Raw text: {text}")
                                        else:
                                            print(f"Summary: {text}")
                    else:
                        response_json = json.loads(response.text)
                        print(f"Parsed Response: {json.dumps(response_json, indent=2)}")
                except json.JSONDecodeError:
                    pass  # Response is not JSON, already printed above
                    
            except Exception as e:
                print(f"Error: {e}")

async def chat_with_agentcore():
    """
    Chat with AgentCore using the same approach as test_mcp_endpoint but for conversational queries
    """
    agent_arn = "arn:aws:bedrock-agentcore:us-west-2:010526247135:runtime/hosted_agent_gy1a5-1a1kINFh9p"
    
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # Create a conversational request - you might need to adjust this based on your MCP server's expected format
    chat_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search",  # Using the search tool that works in test_mcp_endpoint
            "arguments": {
                "index": "events",
                "query_body": {
                    "query": {
                        "bool": {
                            "should": [
                                {"match": {"name": "paris"}},
                                {"match": {"description": "paris"}},
                                {"match": {"venue": "paris"}},
                                {"match": {"address": "paris"}}
                            ]
                        }
                    },
                    "size": 10
                }
            }
        }
    }
    
    aws_auth = AWSAuth()
    
    async with httpx.AsyncClient() as client:
        body = json.dumps(chat_request)
        headers = aws_auth.get_auth_headers(mcp_url, body=body)
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json, text/event-stream"
        
        print(f"\n--- Chat Query: Events in Paris ---")
        print(f"Request: {json.dumps(chat_request, indent=2)}")
        
        try:
            response = await client.post(mcp_url, headers=headers, content=body)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
            
            # Parse and display results
            try:
                if response.text.startswith('data: '):
                    json_part = response.text[6:]
                    response_json = json.loads(json_part)
                    print(f"Parsed Response: {json.dumps(response_json, indent=2)}")
                    
                    # Extract and display search results in a conversational format
                    result = response_json.get('result', {})
                    if 'content' in result:
                        for content_item in result['content']:
                            if content_item['type'] == 'text':
                                text = content_item['text']
                                if text.startswith('[{') and text.endswith('}]'):
                                    try:
                                        search_results = json.loads(text)
                                        print(f"\n🎉 I found {len(search_results)} events in Paris:")
                                        for i, event in enumerate(search_results, 1):
                                            print(f"\n{i}. {event.get('name', 'Unnamed Event')}")
                                            print(f"   📍 {event.get('venue', 'TBD')} - {event.get('address', 'Address TBD')}")
                                            print(f"   📅 {event.get('start_date', 'Date TBD')}")
                                            if event.get('description'):
                                                print(f"   📝 {event.get('description')}")
                                            if event.get('price_range'):
                                                print(f"   💰 {event.get('price_range')}")
                                            if event.get('booking_url'):
                                                print(f"   🎫 {event.get('booking_url')}")
                                    except json.JSONDecodeError:
                                        print(f"Response: {text}")
                                else:
                                    print(f"Response: {text}")
                else:
                    response_json = json.loads(response.text)
                    print(f"Parsed Response: {json.dumps(response_json, indent=2)}")
            except json.JSONDecodeError:
                pass
                
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    print("=== Testing MCP Endpoint ===")
    asyncio.run(test_mcp_endpoint())
    
    print("\n=== Chat with AgentCore (HTTP) ===")
    asyncio.run(chat_with_agentcore())