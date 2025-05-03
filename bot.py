import os
import boto3
import json
import discord
import asyncio
import time
import logging
from discord.ext import commands
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize CloudWatch metrics
cloudwatch = boto3.client('cloudwatch')

def put_metric(name, value, unit='Count'):
    """Put a metric to CloudWatch."""
    try:
        cloudwatch.put_metric_data(
            Namespace='RvarOastDen',
            MetricData=[{
                'MetricName': name,
                'Value': value,
                'Unit': unit,
                'Timestamp': time.time()
            }]
        )
    except Exception as e:
        logger.error(f"Failed to put metric {name}: {e}")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

dynamo = boto3.resource("dynamodb")
memory_table = dynamo.Table(os.environ["MEMORY_TABLE"])

def get_token_from_secrets(secret_arn):
    """
    Retrieve the Discord bot token from AWS Secrets Manager.
    
    Args:
        secret_arn (str): The ARN of the secret in Secrets Manager
        
    Returns:
        str: The Discord bot token if successful, None otherwise
    """
    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])
        return secret["DISCORD_TOKEN"]
    except ClientError as e:
        logger.error(f"Error retrieving secret: {e}")
        put_metric('SecretRetrievalError', 1)
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"Error parsing secret: {e}")
        put_metric('SecretParsingError', 1)
        return None

def call_claude(prompt):
    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
    start_time = time.time()
    try:
        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "anthropic_version": "bedrock-2023-05-31"
            })
        )
        result = json.loads(response["body"].read())
        response_time = time.time() - start_time
        put_metric('ClaudeResponseTime', response_time, 'Seconds')
        put_metric('ClaudeSuccess', 1)
        return result["content"][0]["text"]
    except Exception as e:
        logger.error(f"Claude error: {e}")
        put_metric('ClaudeError', 1)
        return "🤖 Claude had a meltdown."

def save_memory(bot_name, text):
    try:
        memory_table.put_item(Item={
            "bot_name": bot_name,
            "timestamp": str(int(time.time())),
            "text": text
        })
        put_metric('MemorySaved', 1)
    except Exception as e:
        logger.error(f"Failed to save memory: {e}")
        put_metric('MemorySaveError', 1)

def load_memory(bot_name, limit=5):
    try:
        resp = memory_table.query(
            KeyConditionExpression=Key("bot_name").eq(bot_name),
            Limit=limit,
            ScanIndexForward=False
        )
        put_metric('MemoryLoaded', 1)
        return [item["text"] for item in resp.get("Items", [])]
    except Exception as e:
        logger.error(f"Failed to load memory: {e}")
        put_metric('MemoryLoadError', 1)
        return []

def roast_response(question, memories):
    prompt = (
        f"You are a bold, sarcastic, insightful Discord bot. "
        f"You are replying to this message: '{question}'\n"
        f"You remember:\n" + "\n".join(memories) + "\n"
        f"Respond with humor, roasting, or insight. Do not be polite."
    )
    return call_claude(prompt)

@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user}")
    put_metric('BotStartup', 1)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("That's not a command I recognize. Try !help for available commands.")
        put_metric('CommandNotFound', 1)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You're missing a required argument. Check !help for usage.")
        put_metric('MissingArgument', 1)
    else:
        logger.error(f"Command error: {error}")
        put_metric('CommandError', 1)
        await ctx.send("Something went wrong. Please try again.")

@bot.command(name="ask")
async def ask(ctx, *, question):
    if not question.strip():
        await ctx.send("Please provide a question to ask.")
        return

    await ctx.send("Consulting my corrupted memories...")
    mem = load_memory("FordBot")
    reply = roast_response(question, mem)
    save_memory("FordBot", f"Q: {question} | A: {reply}")
    await ctx.send(reply)
    put_metric('AskCommand', 1)

def handler(event, context):
    """
    Lambda handler function that starts the Discord bot.
    
    Args:
        event: AWS Lambda event
        context: AWS Lambda context
        
    Returns:
        None
    """
    token = get_token_from_secrets(os.environ["DISCORD_SECRET_ARN"])
    if not token:
        logger.error("Failed to retrieve Discord token from Secrets Manager")
        return
    
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start(token))
    loop.run_forever()
