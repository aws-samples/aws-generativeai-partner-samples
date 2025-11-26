#!/usr/bin/env python3
"""Test script for AgentCore-compatible endpoints."""

import asyncio
import json
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8080"


def test_ping_endpoint():
    """Test the /ping health check endpoint."""
    print("Testing /ping endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/ping", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_invocations_endpoint():
    """Test the /invocations endpoint."""
    print("\nTesting /invocations endpoint...")
    
    test_payload = {
        "prompt": "Show me all tables in the database",
        "context": {"user_id": "test_user"},
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/invocations",
            json=test_payload,
            timeout=30,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_streaming_endpoint():
    """Test the /invocations endpoint with streaming."""
    print("\nTesting /invocations endpoint with streaming...")
    
    test_payload = {
        "prompt": "List all users from the users table",
        "stream": True
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/invocations",
            json=test_payload,
            timeout=30,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        print(f"Status Code: {response.status_code}")
        print("Streaming response:")
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = decoded_line[6:]  # Remove 'data: ' prefix
                    if data != '[DONE]':
                        try:
                            parsed = json.loads(data)
                            print(f"  {parsed}")
                        except json.JSONDecodeError:
                            print(f"  {data}")
                    else:
                        print("  Stream ended")
                        break
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_schema_endpoint():
    """Test the /schema endpoint."""
    print("\nTesting /schema endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/schema", timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            schema = response.json()
            print(f"Found {len(schema)} tables")
            for table in schema[:2]:  # Show first 2 tables
                print(f"  Table: {table.get('name', 'unknown')}")
        else:
            print(f"Response: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_root_endpoint():
    """Test the root endpoint."""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests."""
    print("AgentCore Endpoint Testing")
    print("=" * 40)
    
    tests = [
        ("Health Check", test_ping_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("Schema Endpoint", test_schema_endpoint),
        ("Invocations (JSON)", test_invocations_endpoint),
        ("Invocations (Streaming)", test_streaming_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 40)
    print("Test Results Summary:")
    print("=" * 40)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    total_passed = sum(1 for _, success in results if success)
    print(f"\nPassed: {total_passed}/{len(results)} tests")
    
    if total_passed == len(results):
        print("🎉 All tests passed! AgentCore endpoints are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    main()