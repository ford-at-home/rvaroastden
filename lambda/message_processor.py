"""
Lambda function to process messages from SQS queue
Generates AI responses without handling Discord directly
"""

import os
import boto3
import json
import time
import logging
from typing import Dict, Any, List
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# Initialize AWS clients lazily
bedrock = None
dynamodb = None
cloudwatch = None
memory_table = None

# Environment variables
MEMORY_TABLE = os.environ.get("MEMORY_TABLE", "SimulchaosMemory")


def init_aws_clients():
    """Initialize AWS clients - called once when needed"""
    global bedrock, dynamodb, cloudwatch, memory_table
    if not bedrock:
        bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    if not dynamodb:
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    if not cloudwatch:
        cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
    if not memory_table and MEMORY_TABLE:
        memory_table = dynamodb.Table(MEMORY_TABLE)


def put_metric(name: str, value: float, unit: str = "Count") -> None:
    """Put a metric to CloudWatch."""
    init_aws_clients()
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
    init_aws_clients()
    start_time = time.time()
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
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
    init_aws_clients()
    if not memory_table:
        logger.warning("Memory table not configured")
        return

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
    init_aws_clients()
    if not memory_table:
        logger.warning("Memory table not configured")
        return []

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
        # In Lambda, personalities are in a layer at /opt
        personality_file = f"/opt/{bot_name.lower()}.json"
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

    response = call_claude(prompt)
    logger.info(f"Generated roast response: {response[:100]}...")

    # Check for duplicate content (sometimes Claude might repeat)
    lines = response.split("\n")
    if len(lines) == 2 and lines[0].strip() == lines[1].strip():
        logger.warning(f"Detected duplicate lines in response, deduplicating")
        response = lines[0].strip()

    return response


def generate_autonomous_response(
    question: str, memories: List[str], bot_name: str, context: str, reply_reason: str
) -> str:
    """Generate an autonomous conversation response using Claude"""
    # Load personality from JSON
    personality = load_personality(bot_name)
    personality_prompt = build_personality_prompt(personality)

    # Add context for autonomous replies
    autonomous_context = f"""
You are naturally joining this conversation as {personality['name']}.

Your conversation style: {personality.get('conversation_style', 'Natural and engaging')}
Why you're replying: {reply_reason}

Remember:
- This is NOT a direct command/roast request - you're naturally joining a conversation
- Be conversational and authentic to your personality
- Don't announce that you're responding or make it obvious you're AI
- React naturally to what was said
- Stay in character but be organic

Recent conversation context:
{context}
"""

    memory_context = (
        "\\n".join(memories) if memories else "No previous conversations to remember."
    )

    prompt = f"""{personality_prompt}

{autonomous_context}

Previous conversations you remember:
{memory_context}

Most recent message: "{question}"

Respond naturally as {personality['name']} would in this conversation. Keep it under 200 characters for Discord.
Be authentic to your personality and the flow of conversation."""

    response = call_claude(prompt)
    logger.info(f"Generated autonomous response: {response[:100]}...")

    # Check for duplicate content (sometimes Claude might repeat)
    lines = response.split("\\n")
    if len(lines) == 2 and lines[0].strip() == lines[1].strip():
        logger.warning(
            f"Detected duplicate lines in autonomous response, deduplicating"
        )
        response = lines[0].strip()

    return response


def process_roast_request(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process a roast request from SQS"""
    bot_name = message_data.get("bot_name", "FordBot")
    question = message_data.get("question", "")
    user_name = message_data.get("user_name", "Unknown")

    logger.info(f"Processing roast request from {user_name}: {question}")

    # Load memories
    memories = load_memory(bot_name)

    # Generate response
    response = generate_roast_response(question, memories, bot_name)

    # Save to memory
    memory_entry = f"Q: {question} (by {user_name}) | A: {response}"
    save_memory(bot_name, memory_entry)

    # Return response data for bot to handle
    return {
        "success": True,
        "response": response,
        "bot_name": bot_name,
        "original_message": message_data,
    }


def process_autonomous_reply(message_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process an autonomous conversation reply from SQS"""
    bot_name = message_data.get("bot_name", "FordBot")
    question = message_data.get("question", "")
    user_name = message_data.get("user_name", "Unknown")
    context = message_data.get("context", "")
    reply_reason = message_data.get("reply_reason", "Natural conversation flow")

    logger.info(
        f"Processing autonomous reply from {bot_name}: {question[:50]}... (Reason: {reply_reason})"
    )

    # Load memories
    memories = load_memory(bot_name)

    # Generate response
    response = generate_autonomous_response(
        question, memories, bot_name, context, reply_reason
    )

    # Save to memory - autonomous replies are also part of conversation history
    memory_entry = f"Autonomous: {question} (by {user_name}) | Response: {response} | Reason: {reply_reason}"
    save_memory(bot_name, memory_entry, "autonomous_conversation")

    # Return response data for bot to handle
    return {
        "success": True,
        "response": response,
        "bot_name": bot_name,
        "original_message": message_data,
        "type": "autonomous_reply",
    }


def update_discord_message(
    channel_id: str, message_id: str, content: str, bot_name: str = "FordBot"
) -> bool:
    """Update a Discord message using the REST API"""
    logger.info(
        f"Updating Discord message {message_id} in channel {channel_id} with content: {content[:50]}..."
    )

    # Add a small delay to avoid Discord display issues
    time.sleep(0.5)

    try:
        # Get Discord token from environment or Secrets Manager based on bot name
        discord_token = os.environ.get("DISCORD_TOKEN")
        if not discord_token:
            # Map bot names to secret names
            secret_map = {
                "FordBot": "simulchaos/discord",
                "AprilBot": "simulchaos/discord-april",
                "AdamBot": "simulchaos/discord-adam",
            }
            secret_name = secret_map.get(bot_name, "simulchaos/discord")

            # Try to get from Secrets Manager
            init_aws_clients()
            secrets_client = boto3.client("secretsmanager", region_name="us-east-1")
            try:
                secret_response = secrets_client.get_secret_value(SecretId=secret_name)
                secret_data = json.loads(secret_response["SecretString"])
                discord_token = secret_data.get("DISCORD_TOKEN")
                logger.info(f"Using token from {secret_name} for {bot_name}")
            except Exception as e:
                logger.error(f"Failed to get Discord token from Secrets Manager: {e}")
                return False

        if not discord_token:
            logger.error("No Discord token available")
            return False

        # Update message via Discord REST API
        import urllib3

        http = urllib3.PoolManager()

        url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        headers = {
            "Authorization": f"Bot {discord_token}",
            "Content-Type": "application/json",
        }

        # Ensure content is clean and not duplicated
        clean_content = content.strip()

        # Check if content appears to be duplicated
        if len(clean_content) > 100:
            half_len = len(clean_content) // 2
            first_half = clean_content[:half_len]
            second_half = clean_content[half_len : half_len * 2]
            if first_half == second_half:
                logger.warning(
                    "Content appears to be duplicated, using first half only"
                )
                clean_content = first_half

        body_data = {"content": clean_content}
        logger.info(f"Sending Discord update with body: {json.dumps(body_data)}")

        response = http.request(
            "PATCH", url, body=json.dumps(body_data).encode("utf-8"), headers=headers
        )

        if response.status == 200:
            logger.info(f"Successfully updated Discord message {message_id}")
            put_metric("DiscordUpdateSuccess", 1)
            return True
        else:
            logger.error(
                f"Failed to update Discord message: {response.status} - {response.data}"
            )
            put_metric("DiscordUpdateError", 1)
            return False

    except Exception as e:
        logger.error(f"Error updating Discord message: {e}")
        put_metric("DiscordUpdateError", 1)
        return False


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for SQS events"""
    logger.info(f"Processing {len(event.get('Records', []))} messages")

    results = []

    for record in event.get("Records", []):
        try:
            # Parse SQS message
            message_body = json.loads(record["body"])
            message_type = message_body.get("type")

            if message_type == "roast_request":
                result = process_roast_request(message_body)
            elif message_type == "autonomous_reply":
                result = process_autonomous_reply(message_body)

                # If successful, update the Discord message
                if result.get("success"):
                    channel_id = message_body.get("channel_id")
                    message_id = message_body.get("message_id")
                    response = result.get("response")

                    if channel_id and message_id and response:
                        bot_name = message_body.get("bot_name", "FordBot")
                        update_success = update_discord_message(
                            channel_id, message_id, response, bot_name
                        )
                        result["discord_updated"] = update_success
                    else:
                        logger.warning(
                            "Missing channel_id, message_id, or response for Discord update"
                        )
                        result["discord_updated"] = False

                results.append(result)
                put_metric("MessageProcessed", 1)
            else:
                logger.warning(f"Unknown message type: {message_type}")
                put_metric("UnknownMessageType", 1)
                results.append(
                    {"success": False, "error": f"Unknown message type: {message_type}"}
                )

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
                "results": results,
            }
        ),
    }
