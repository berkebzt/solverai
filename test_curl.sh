#!/bin/bash

echo "=================================="
echo "  SolverAI API Quick Test"
echo "=================================="
echo ""

BASE_URL="http://localhost:8000"

# Test 1: Health Check
echo "1. Testing health endpoint..."
curl -s $BASE_URL/health | jq '.'
echo ""

# Test 2: API Info
echo "2. Testing root endpoint..."
curl -s $BASE_URL/ | jq '.'
echo ""

# Test 3: Simple Chat
echo "3. Testing chat (this will take a few seconds)..."
RESPONSE=$(curl -s -X POST $BASE_URL/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Please introduce yourself in one sentence.",
    "stream": false
  }')

echo "$RESPONSE" | jq '.'

# Extract conversation ID for next test
CONV_ID=$(echo "$RESPONSE" | jq -r '.conversation_id')

if [ "$CONV_ID" != "null" ] && [ ! -z "$CONV_ID" ]; then
    echo ""
    echo "4. Testing conversation retrieval..."
    curl -s "$BASE_URL/conversations/$CONV_ID" | jq '.messages[] | {role, content}'
    echo ""
fi

echo ""
echo "=================================="
echo "  Tests Complete!"
echo "=================================="
