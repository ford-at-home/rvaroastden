"""
Lambda function to process messages from SQS queue
Handles AI responses and updates Discord messages
"""

import os
import boto3
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import discord
from discord.ext import commands

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
dynamodb = boto3.resource("dynamodb")
cloudwatch = boto3.client("cloudwatch")

# Environment variables
MEMORY_TABLE = os.environ.get("MEMORY_TABLE")
memory_table = dynamodb.Table(MEMORY_TABLE)

# Initialize Discord client for webhook updates
intents = discord.Intents.default()
discord_client = discord.Client(intents=intents)


def put_metric(name: str, value: float, unit: str = "Count") -> None:
    """Put a metric to CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace="RvarOastDen",
            MetricData=[
                {
                    "MetricName": name,
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": datetime.utcnow(),
                }
            ],
        )
    except Exception as e:
        logger.error(f"Failed to put metric {name}: {e}")


def call_claude(prompt: str) -> str:
    """Call Claude AI for response generation"""
    start_time = time.time()
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(
                {
                    "messages": [{"role": "user", "content": prompt}],
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 500,
                    "temperature": 0.8,
                }
            ),
        )
        result = json.loads(response["body"].read())
        response_time = time.time() - start_time

        put_metric("ClaudeResponseTime", response_time, "Seconds")
        put_metric("ClaudeSuccess", 1)

        return result["content"][0]["text"]
    except Exception as e:
        logger.error(f"Claude error: {e}")
        put_metric("ClaudeError", 1)
        return "🤖 *sparks fly* My circuits are fried. Try again later!"


def save_memory(bot_name: str, content: str, memory_type: str = "conversation") -> None:
    """Save memory to DynamoDB"""
    try:
        memory_table.put_item(
            Item={
                "bot_name": bot_name,
                "timestamp": str(int(time.time())),
                "content": content,
                "type": memory_type,
                "ttl": int(time.time()) + (30 * 24 * 60 * 60),  # 30 days TTL
            }
        )
        put_metric("MemorySaved", 1)
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")
        put_metric("MemorySaveError", 1)


def load_memory(bot_name: str, limit: int = 10) -> List[str]:
    """Load recent memories from DynamoDB"""
    try:
        response = memory_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("bot_name").eq(
                bot_name
            ),
            Limit=limit,
            ScanIndexForward=False,  # Most recent first
        )
        put_metric("MemoryLoaded", 1)
        return [item["content"] for item in response.get("Items", [])]
    except Exception as e:
        logger.error(f"Failed to load memory: {e}")
        put_metric("MemoryLoadError", 1)
        return []


def load_personality(bot_name: str) -> Dict[str, Any]:
    """Load personality from JSON file"""
    try:
        # In Lambda, personalities would be packaged with deployment
        personality_file = f"/opt/personalities/{bot_name.lower()}.json"
        with open(personality_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Personality file not found for {bot_name}, using default")
        return {
            "name": bot_name,
            "traits": ["witty", "sarcastic"],
            "roast_style": "Clever observations with humor",
            "catchphrases": [],
            "interests": ["technology", "internet culture"],
        }


def build_personality_prompt(personality: Dict[str, Any]) -> str:
    """Build a comprehensive personality prompt from JSON data"""
    traits = ", ".join(personality.get("traits", []))
    description = personality.get("description", "A witty Discord bot")
    roast_style = personality.get("roast_style", "Clever and funny")
    catchphrases = personality.get("catchphrases", [])
    interests = ", ".join(personality.get("interests", []))

    prompt_parts = [
        f"You are {personality['name']}, {description}",
        f"Your core traits: {traits}",
        f"Your roasting style: {roast_style}",
        f"Topics you're interested in: {interests}",
    ]

    if catchphrases:
        prompt_parts.append(f"You often say things like: {', '.join(catchphrases[:3])}")

    if "speech_patterns" in personality:
        patterns = " ".join(personality["speech_patterns"][:2])
        prompt_parts.append(f"Your speech style: {patterns}")

    return "\n".join(prompt_parts)


def generate_roast_response(
    question: str, memories: List[str], bot_name: str = "FordBot"
) -> str:
    """Generate a roast response using Claude"""
    # Load personality from JSON
    personality = load_personality(bot_name)
    personality_prompt = build_personality_prompt(personality)

    # Add specific context for roasting
    roast_context = f"""
Remember your roasting approach: {personality.get('roast_style', 'Be witty and clever')}

Common targets you roast: {', '.join(personality.get('roast_targets', ['pretension', 'hypocrisy'])[:3])}

Your emotional baseline: {personality.get('emotional_range', {}).get('baseline', 'Witty and engaged')}
"""

    memory_context = (
        "\n".join(memories) if memories else "No previous conversations to remember."
    )

    prompt = f"""{personality_prompt}

{roast_context}

Previous conversations you remember:
{memory_context}

User's message: "{question}"

Respond with a witty roast or clever observation. Keep it under 200 characters for Discord.
Be creative, funny, and true to your personality. Don't be generic or polite."""

    return call_claude(prompt)


async def update_discord_message(
    channel_id: str, message_id: str, content: str, token: str
) -> bool:
    """Update a Discord message via webhook or bot edit"""
    try:
        # Initialize bot if not already connected
        if not discord_client.is_ready():
            await discord_client.login(token)

        # Get channel and message
        channel = discord_client.get_channel(int(channel_id))
        if not channel:
            channel = await discord_client.fetch_channel(int(channel_id))

        message = await channel.fetch_message(int(message_id))
        await message.edit(content=content)

        put_metric("DiscordMessageUpdated", 1)
        return True
    except Exception as e:
        logger.error(f"Failed to update Discord message: {e}")
        put_metric("DiscordUpdateError", 1)
        return False


def process_roast_request(
    message_data: Dict[str, Any], discord_token: str
) -> Dict[str, Any]:
    """Process a roast request from SQS"""
    bot_name = message_data.get("bot_name", "FordBot")
    question = message_data.get("question", "")
    channel_id = message_data.get("channel_id")
    message_id = message_data.get("message_id")
    user_name = message_data.get("user_name", "Unknown")

    logger.info(f"Processing roast request from {user_name}: {question}")

    # Load memories
    memories = load_memory(bot_name)

    # Generate response
    response = generate_roast_response(question, memories, bot_name)

    # Save to memory
    memory_entry = f"Q: {question} (by {user_name}) | A: {response}"
    save_memory(bot_name, memory_entry)

    # Update Discord message
    # Note: In production, we'd use webhooks or a separate service for this
    # For now, we'll return the response to be handled by the container

    return {
        "success": True,
        "response": response,
        "channel_id": channel_id,
        "message_id": message_id,
    }


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events"""
    logger.info(f"Processing {len(event.get('Records', []))} messages")

    results = []
    discord_token = None  # TODO: Get from secrets manager

    for record in event.get("Records", []):
        try:
            # Parse SQS message
            message_body = json.loads(record["body"])
            message_type = message_body.get("type")

            if message_type == "roast_request":
                result = process_roast_request(message_body, discord_token)
                results.append(result)
                put_metric("MessageProcessed", 1)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                put_metric("UnknownMessageType", 1)

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            put_metric("MessageProcessingError", 1)
            results.append({"success": False, "error": str(e)})

    # Return successful if any messages were processed successfully
    successful = sum(1 for r in results if r.get("success", False))

    return {
        "statusCode": 200 if successful > 0 else 500,
        "body": json.dumps(
            {
                "processed": len(results),
                "successful": successful,
                "failed": len(results) - successful,
            }
        ),
    }
