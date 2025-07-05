"""
Discord Bot Container for AI Roast Den
Runs persistently in Fargate and sends messages to SQS for processing
"""

import os
import boto3
import json
import discord
import asyncio
import time
import logging
from datetime import datetime
from discord.ext import commands
from typing import Optional, Dict, Any
from threading import Thread
import socket

# Configure structured logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
sqs = boto3.client("sqs")
cloudwatch = boto3.client("cloudwatch")
secrets_client = boto3.client("secretsmanager")

# Global variables
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
HEALTH_CHECK_PORT = 8080


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


class SimpleHealthServer:
    """Simple TCP health check server"""

    def __init__(self, bot):
        self.bot = bot
        self.server = None
        self.running = False

    def start(self):
        """Start health check server in a thread"""
        self.running = True
        self.thread = Thread(target=self._run_server, daemon=True)
        self.thread.start()
        logger.info(f"Health check server started on port {HEALTH_CHECK_PORT}")

    def _run_server(self):
        """Run the TCP server"""
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("0.0.0.0", HEALTH_CHECK_PORT))
        self.server.listen(5)

        while self.running:
            try:
                self.server.settimeout(1.0)
                client, addr = self.server.accept()
                # Simple HTTP response
                if self.bot.is_ready():
                    response = b"HTTP/1.1 200 OK\r\n\r\nOK"
                else:
                    response = b"HTTP/1.1 503 Service Unavailable\r\n\r\nBot not ready"
                client.send(response)
                client.close()
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Health check error: {e}")

    def stop(self):
        """Stop the health check server"""
        self.running = False
        if self.server:
            self.server.close()


class RoastBot(commands.Bot):
    """Enhanced Discord bot that sends messages to SQS for processing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_time = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        put_metric("BotStartup", 1)

        # Send heartbeat every 30 seconds
        self.loop.create_task(self.heartbeat())

    async def heartbeat(self):
        """Send periodic heartbeat metrics"""
        while not self.is_closed():
            put_metric("BotHeartbeat", 1)
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            put_metric("BotUptime", uptime, "Seconds")
            await asyncio.sleep(30)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # Ignore messages from bots
        if message.author.bot:
            return

        # Process commands
        await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(
                "That's not a command I recognize. Try !help for available commands."
            )
            put_metric("CommandNotFound", 1)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("You're missing a required argument. Check !help for usage.")
            put_metric("MissingArgument", 1)
        else:
            logger.error(f"Command error: {error}")
            put_metric("CommandError", 1)
            self.error_count += 1
            await ctx.send("Something went wrong. Please try again.")


def send_to_sqs(message_data: Dict[str, Any]) -> bool:
    """Send message to SQS for processing"""
    try:
        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_data),
            MessageAttributes={
                "timestamp": {
                    "StringValue": str(int(time.time())),
                    "DataType": "Number",
                },
                "bot_name": {
                    "StringValue": message_data.get("bot_name", "FordBot"),
                    "DataType": "String",
                },
            },
        )
        logger.info(f"Sent message to SQS: {response['MessageId']}")
        put_metric("SQSMessageSent", 1)
        return True
    except Exception as e:
        logger.error(f"Failed to send message to SQS: {e}")
        put_metric("SQSMessageError", 1)
        return False


# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = RoastBot(
    command_prefix="!", intents=intents, help_command=None
)  # Disable default help


@bot.command(name="ask")
async def ask(ctx, *, question: str):
    """Ask the bot a question for a roast response"""
    if not question.strip():
        await ctx.send("Please provide a question to ask.")
        return

    # Send initial response
    processing_msg = await ctx.send("🔥 Cooking up a roast...")

    # Determine which bot to use (rotate between Ford, April, and Adam)
    # TODO: Make this configurable per channel or user command
    bot_names = ["FordBot", "AprilBot", "AdamBot"]
    bot_name = bot_names[hash(ctx.channel.id) % len(bot_names)]

    # Prepare message for SQS
    message_data = {
        "type": "roast_request",
        "bot_name": bot_name,
        "channel_id": str(ctx.channel.id),
        "message_id": str(processing_msg.id),
        "user_id": str(ctx.author.id),
        "user_name": ctx.author.name,
        "question": question,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Send to SQS for processing
    if send_to_sqs(message_data):
        bot.message_count += 1
        put_metric("AskCommand", 1)
        # The Lambda will edit the message with the actual response
    else:
        await processing_msg.edit(
            content="Sorry, I'm having trouble processing that right now. Try again later!"
        )


@bot.command(name="status")
async def status(ctx):
    """Check bot status"""
    uptime = datetime.utcnow() - bot.start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    embed = discord.Embed(title="🤖 Bot Status", color=discord.Color.green())
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Messages Processed", value=bot.message_count, inline=True)
    embed.add_field(name="Errors", value=bot.error_count, inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)

    await ctx.send(embed=embed)
    put_metric("StatusCommand", 1)


@bot.command(name="summon")
async def summon(ctx, bot_name: str, *, question: str):
    """Summon a specific bot personality for a roast"""
    # Validate bot name
    valid_bots = ["FordBot", "AprilBot", "AdamBot", "ford", "april", "adam"]
    bot_name_lower = bot_name.lower()

    if bot_name_lower not in [b.lower() for b in valid_bots]:
        await ctx.send(f"I don't know {bot_name}! Try: FordBot, AprilBot, or AdamBot")
        return

    # Normalize bot name
    if bot_name_lower in ["ford", "fordbot"]:
        bot_name = "FordBot"
    elif bot_name_lower in ["april", "aprilbot"]:
        bot_name = "AprilBot"
    elif bot_name_lower in ["adam", "adambot"]:
        bot_name = "AdamBot"

    # Send initial response with personality indicator
    emoji_map = {"FordBot": "🧘‍♂️", "AprilBot": "🎪", "AdamBot": "🥁"}
    emoji = emoji_map.get(bot_name, "🔥")
    processing_msg = await ctx.send(
        f"{emoji} *{bot_name} is channeling their energy...*"
    )

    # Prepare message for SQS
    message_data = {
        "type": "roast_request",
        "bot_name": bot_name,
        "channel_id": str(ctx.channel.id),
        "message_id": str(processing_msg.id),
        "user_id": str(ctx.author.id),
        "user_name": ctx.author.name,
        "question": question,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Send to SQS for processing
    if send_to_sqs(message_data):
        bot.message_count += 1
        put_metric("SummonCommand", 1)
        put_metric(f"Summon_{bot_name}", 1)
    else:
        await processing_msg.edit(
            content="Sorry, the summoning failed. Try again later!"
        )


@bot.command(name="help")
async def help_command(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="AI Roast Den Commands",
        description="Here are the available commands:",
        color=discord.Color.blue(),
    )
    embed.add_field(
        name="!ask <question>",
        value="Ask me anything for a personality-driven roast response",
        inline=False,
    )
    embed.add_field(
        name="!summon <bot> <question>",
        value="Summon a specific bot: FordBot, AprilBot, or AdamBot\nExample: !summon adam Tell me about startup dynamics",
        inline=False,
    )
    embed.add_field(
        name="!status", value="Check my current status and statistics", inline=False
    )
    embed.add_field(name="!help", value="Show this help message", inline=False)

    await ctx.send(embed=embed)
    put_metric("HelpCommand", 1)


async def main():
    """Main function to run the bot"""
    # Start health check server
    health_server = SimpleHealthServer(bot)
    health_server.start()

    try:
        # Start the bot
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        put_metric("BotCrash", 1)
    finally:
        health_server.stop()
        await bot.close()


if __name__ == "__main__":
    # Validate environment
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set in environment")
        exit(1)

    if not SQS_QUEUE_URL:
        logger.error("SQS_QUEUE_URL not set in environment")
        exit(1)

    # Run the bot
    asyncio.run(main())
