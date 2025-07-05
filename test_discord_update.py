#!/usr/bin/env python3
"""Test Discord message update to debug duplication issue"""
import os
import json
import urllib3
import boto3
from datetime import datetime


def get_discord_token():
    """Get Discord token from Secrets Manager"""
    secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
    response = secrets_client.get_secret_value(SecretId="simulchaos/discord")
    secret_data = json.loads(response["SecretString"])
    return secret_data.get("DISCORD_TOKEN")


def update_discord_message(channel_id: str, message_id: str, content: str, token: str):
    """Update a Discord message"""
    http = urllib3.PoolManager()

    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
    headers = {"Authorization": f"Bot {token}", "Content-Type": "application/json"}

    body = json.dumps({"content": content})
    print(f"Updating message {message_id} with: {content}")
    print(f"Request body: {body}")

    response = http.request("PATCH", url, body=body.encode("utf-8"), headers=headers)

    print(f"Response status: {response.status}")
    print(f"Response data: {response.data.decode('utf-8')}")

    return response.status == 200


def main():
    """Test Discord update with a real message"""
    # Get these values from a recent Discord message
    channel_id = input("Enter channel ID: ")
    message_id = input("Enter message ID to update: ")

    # Get token
    token = get_discord_token()

    # Test updates
    test_messages = [
        f"Test update 1: {datetime.now().isoformat()}",
        "Test update 2: This is a single line message",
        "Test update 3: First line\nSecond line\nThird line",
        "Test update 4: Final message",
    ]

    for i, content in enumerate(test_messages):
        print(f"\n--- Test {i+1} ---")
        success = update_discord_message(channel_id, message_id, content, token)
        if not success:
            print("Update failed!")
            break
        input("Check Discord and press Enter to continue...")


if __name__ == "__main__":
    main()
