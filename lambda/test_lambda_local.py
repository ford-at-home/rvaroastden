#!/usr/bin/env python3
"""
Test the Lambda function locally with sample SQS messages
"""
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables for testing
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["MEMORY_TABLE"] = "SimulchaosMemory"
os.environ["LOG_LEVEL"] = "INFO"

import message_processor

# Sample test messages
test_messages = [
    {
        "type": "roast_request",
        "bot_name": "FordBot",
        "question": "What do you think about JavaScript?",
        "channel_id": "123456789",
        "message_id": "987654321",
        "user_id": "111111111",
        "user_name": "TestUser",
        "timestamp": "2025-07-05T10:00:00",
    },
    {
        "type": "roast_request",
        "bot_name": "AprilBot",
        "question": "Tell me about startups",
        "channel_id": "123456789",
        "message_id": "987654322",
        "user_id": "111111112",
        "user_name": "TestUser2",
        "timestamp": "2025-07-05T10:01:00",
    },
    {
        "type": "roast_request",
        "bot_name": "AdamBot",
        "question": "How do systems work?",
        "channel_id": "123456789",
        "message_id": "987654323",
        "user_id": "111111113",
        "user_name": "TestUser3",
        "timestamp": "2025-07-05T10:02:00",
    },
]


def test_single_message(message):
    """Test processing a single message"""
    print(f"\n{'='*60}")
    print(f"Testing {message['bot_name']} with: {message['question']}")
    print(f"{'='*60}")

    # Create SQS event structure
    event = {"Records": [{"body": json.dumps(message)}]}

    # Process message
    result = message_processor.handler(event, None)

    # Parse results
    body = json.loads(result["body"])

    print(f"Status Code: {result['statusCode']}")
    print(f"Processed: {body['processed']}")
    print(f"Successful: {body['successful']}")
    print(f"Failed: {body['failed']}")

    if body.get("results"):
        for res in body["results"]:
            if res.get("success"):
                print(f"\nResponse from {res['bot_name']}:")
                print(f">>> {res['response']}")
            else:
                print(f"\nError: {res.get('error')}")


def test_batch_messages():
    """Test processing multiple messages at once"""
    print(f"\n{'='*60}")
    print("Testing batch processing of all messages")
    print(f"{'='*60}")

    # Create SQS event with multiple records
    event = {"Records": [{"body": json.dumps(msg)} for msg in test_messages]}

    # Process messages
    result = message_processor.handler(event, None)

    # Parse results
    body = json.loads(result["body"])

    print(f"Status Code: {result['statusCode']}")
    print(f"Total Processed: {body['processed']}")
    print(f"Total Successful: {body['successful']}")
    print(f"Total Failed: {body['failed']}")


if __name__ == "__main__":
    print("Testing Lambda function locally")
    print(
        "Note: This will use default personalities since we don't have access to the personality files"
    )

    # Test individual messages
    for msg in test_messages:
        test_single_message(msg)

    # Test batch processing
    test_batch_messages()

    print("\n✅ Local testing complete!")
