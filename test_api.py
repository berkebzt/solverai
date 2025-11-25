#!/usr/bin/env python3
"""
Test script for SolverAI API

Tests the LLM integration and conversation management
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_health():
    """Test health endpoint"""
    print_section("1. Testing Health Endpoint")

    response = requests.get(f"{BASE_URL}/health")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")

    return response.status_code == 200


def test_root():
    """Test root endpoint"""
    print_section("2. Testing Root Endpoint")

    response = requests.get(f"{BASE_URL}/")
    data = response.json()

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2)}")

    return response.status_code == 200


def test_chat_simple():
    """Test simple chat without streaming"""
    print_section("3. Testing Simple Chat (No Streaming)")

    payload = {
        "message": "What is the capital of France?",
        "stream": False
    }

    print(f"Request: {json.dumps(payload, indent=2)}")
    print("\nSending request...")

    start_time = time.time()
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    elapsed = time.time() - start_time

    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse received in {elapsed:.2f}s")
        print(f"Conversation ID: {data['conversation_id']}")
        print(f"Response: {data['response']}")
        return data['conversation_id']
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None


def test_chat_continuation(conversation_id):
    """Test chat continuation in same conversation"""
    print_section("4. Testing Conversation Continuation")

    payload = {
        "message": "What is its population?",
        "conversation_id": conversation_id,
        "stream": False
    }

    print(f"Request: {json.dumps(payload, indent=2)}")
    print("\nSending request...")

    start_time = time.time()
    response = requests.post(f"{BASE_URL}/chat", json=payload)
    elapsed = time.time() - start_time

    if response.status_code == 200:
        data = response.json()
        print(f"\nResponse received in {elapsed:.2f}s")
        print(f"Response: {data['response']}")
        return True
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return False


def test_get_conversation(conversation_id):
    """Test retrieving conversation history"""
    print_section("5. Testing Get Conversation")

    response = requests.get(f"{BASE_URL}/conversations/{conversation_id}")

    if response.status_code == 200:
        data = response.json()
        print(f"Conversation ID: {data['conversation_id']}")
        print(f"Title: {data['title']}")
        print(f"\nMessages ({len(data['messages'])}):")
        for i, msg in enumerate(data['messages'], 1):
            print(f"\n  {i}. [{msg['role']}]: {msg['content'][:100]}...")
        return True
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return False


def test_list_conversations():
    """Test listing all conversations"""
    print_section("6. Testing List Conversations")

    response = requests.get(f"{BASE_URL}/conversations")

    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['conversations'])} conversations")
        for conv in data['conversations']:
            print(f"\n  - {conv['conversation_id'][:8]}...")
            print(f"    Title: {conv['title']}")
            print(f"    Updated: {conv['updated_at']}")
        return True
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return False


def test_streaming_chat():
    """Test streaming chat"""
    print_section("7. Testing Streaming Chat")

    payload = {
        "message": "Count from 1 to 5 slowly",
        "stream": True
    }

    print(f"Request: {json.dumps(payload, indent=2)}")
    print("\nStreaming response:")
    print("-" * 60)

    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json=payload,
            stream=True,
            timeout=60
        )

        full_response = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data != "[DONE]":
                        print(data, end='', flush=True)
                        full_response += data

        print("\n" + "-" * 60)
        print(f"\nFull response: {full_response}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  SOLVERAI API TEST SUITE")
    print("=" * 60)

    results = {}

    # Test 1: Health
    results['health'] = test_health()

    # Test 2: Root
    results['root'] = test_root()

    # Test 3: Simple chat
    conversation_id = test_chat_simple()
    results['simple_chat'] = conversation_id is not None

    if conversation_id:
        # Test 4: Continuation
        results['continuation'] = test_chat_continuation(conversation_id)

        # Test 5: Get conversation
        results['get_conversation'] = test_get_conversation(conversation_id)
    else:
        results['continuation'] = False
        results['get_conversation'] = False

    # Test 6: List conversations
    results['list_conversations'] = test_list_conversations()

    # Test 7: Streaming (optional)
    print("\nDo you want to test streaming? (y/n): ", end='')
    try:
        choice = input().strip().lower()
        if choice == 'y':
            results['streaming'] = test_streaming_chat()
        else:
            results['streaming'] = None
    except:
        results['streaming'] = None

    # Summary
    print_section("TEST SUMMARY")

    for test_name, result in results.items():
        if result is None:
            status = "SKIPPED"
        elif result:
            status = "✓ PASSED"
        else:
            status = "✗ FAILED"
        print(f"  {test_name.replace('_', ' ').title()}: {status}")

    passed = sum(1 for r in results.values() if r is True)
    total = sum(1 for r in results.values() if r is not None)

    print(f"\n  Total: {passed}/{total} tests passed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
