#!/usr/bin/env python3
"""
Personality-specific Discord bot container
Each bot instance runs with a specific personality
"""
import os
import asyncio
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import discord
from discord.ext import commands
import boto3
import aiohttp
from aiohttp import web
from conversation_monitor import ConversationMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Environment variables
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
BOT_PERSONALITY = os.environ.get(
    "BOT_PERSONALITY", "FordBot"
)  # FordBot, AprilBot, or AdamBot
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL") or os.environ.get("MESSAGE_QUEUE_URL")
MEMORY_TABLE = os.environ.get("MEMORY_TABLE", "SimulchaosMemory")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

# Personality-specific configuration
PERSONALITY_CONFIG = {
    "FordBot": {
        "emoji": "🧘‍♂️",
        "status": "Meditating on your failures",
        "prefix": "!ford",
        "color": discord.Color.blue(),
    },
    "AprilBot": {
        "emoji": "🎪",
        "status": "Juggling your insecurities",
        "prefix": "!april",
        "color": discord.Color.red(),
    },
    "AdamBot": {
        "emoji": "🥁",
        "status": "Drumming up chaos",
        "prefix": "!adam",
        "color": discord.Color.green(),
    },
}

# Get personality config
personality_cfg = PERSONALITY_CONFIG.get(BOT_PERSONALITY, PERSONALITY_CONFIG["FordBot"])

# AWS clients
sqs = boto3.client("sqs", region_name=AWS_REGION)
cloudwatch = boto3.client("cloudwatch", region_name=AWS_REGION)


def put_metric(name: str, value: float, unit: str = "Count") -> None:
    """Put a metric to CloudWatch with personality prefix."""
    try:
        cloudwatch.put_metric_data(
            Namespace="RvarOastDen",
            MetricData=[
                {
                    "MetricName": f"{BOT_PERSONALITY}_{name}",
                    "Value": value,
                    "Unit": unit,
                    "Timestamp": datetime.utcnow(),
                }
            ],
        )
    except Exception as e:
        logger.error(f"Failed to put metric {name}: {e}")


class PersonalityBot(commands.Bot):
    """Bot class for personality-specific behavior"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.personality = BOT_PERSONALITY
        self.start_time = datetime.utcnow()
        self.message_count = 0
        self.error_count = 0
        self.conversation_monitor = None

    async def setup_hook(self):
        """Called when bot is starting up"""
        logger.info(f"Starting {self.personality} bot...")
        # Start periodic tasks
        self.loop.create_task(self.periodic_metrics())

    async def periodic_metrics(self):
        """Send periodic metrics to CloudWatch"""
        await self.wait_until_ready()
        while not self.is_closed():
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
            put_metric("Uptime", uptime, "Seconds")
            put_metric("MessageCount", self.message_count)
            put_metric("ErrorCount", self.error_count)
            await asyncio.sleep(30)

    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        logger.info(f"{self.personality} connected as {self.user} (ID: {self.user.id})")
        
        # Set custom status
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name=personality_cfg["status"]
            )
        )

        # Initialize conversation monitor
        self.conversation_monitor = ConversationMonitor(self, self.personality)
        await self.conversation_monitor.start_monitoring()

        put_metric("BotReady", 1)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        # First, let conversation monitor evaluate for autonomous replies
        if self.conversation_monitor and not message.author.bot:
            await self.conversation_monitor.on_message(message)

        # Then handle explicit commands/mentions
        # Ignore messages from any bot
        if message.author.bot:
            return

        # Only process if bot is mentioned or message starts with our prefix
        bot_mentioned = self.user in message.mentions
        starts_with_prefix = message.content.lower().startswith(
            personality_cfg["prefix"]
        )

        if bot_mentioned or starts_with_prefix:
            # Process commands
            await self.process_commands(message)

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            # Ignore command not found for this personality
            return
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                f"{personality_cfg['emoji']} You're missing something there, chief. Try again with all the details."
            )
            put_metric("MissingArgument", 1)
        else:
            logger.error(f"Command error: {error}")
            put_metric("CommandError", 1)
            self.error_count += 1
            await ctx.send(
                f"{personality_cfg['emoji']} Something went wrong. Even I make mistakes sometimes."
            )


def send_to_sqs(message_data: Dict[str, Any]) -> bool:
    """Send message to SQS for processing"""
    if not SQS_QUEUE_URL:
        logger.warning("SQS not configured - skipping message send")
        return False
        
    try:
        # Always use our personality
        message_data["bot_name"] = BOT_PERSONALITY

        response = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=json.dumps(message_data),
            MessageAttributes={
                "timestamp": {
                    "StringValue": str(int(time.time())),
                    "DataType": "Number",
                }
            },
        )
        logger.info(f"Sent message to SQS: {response['MessageId']}")
        put_metric("SQSSendSuccess", 1)
        return True
    except Exception as e:
        logger.error(f"Failed to send to SQS: {e}")
        put_metric("SQSSendError", 1)
        return False


# Initialize bot with personality-specific settings
intents = discord.Intents.default()
intents.message_content = True
bot = PersonalityBot(
    command_prefix=[personality_cfg["prefix"], f"!{BOT_PERSONALITY.lower()}", "!"],
    intents=intents,
    help_command=None,
)


@bot.command(name="roast")
async def roast(ctx, *, target: str = None):
    """Roast someone or something"""
    if not target:
        target = "your lack of creativity in not providing a target"

    # Send initial response with personality emoji
    processing_msg = await ctx.send(
        f"{personality_cfg['emoji']} *{BOT_PERSONALITY} is preparing a roast...*"
    )

    # Prepare message for SQS
    message_data = {
        "type": "roast_request",
        "bot_name": BOT_PERSONALITY,
        "channel_id": str(ctx.channel.id),
        "message_id": str(processing_msg.id),
        "user_id": str(ctx.author.id),
        "user_name": ctx.author.name,
        "question": f"Roast {target}",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Send to SQS for processing
    if send_to_sqs(message_data):
        bot.message_count += 1
        put_metric("RoastCommand", 1)
    else:
        await processing_msg.edit(
            content=f"{personality_cfg['emoji']} My roasting powers have failed me. Try again later!"
        )


@bot.command(name="ask", aliases=["question", "q"])
async def ask(ctx, *, question: str):
    """Ask a question and get a personality-specific response"""
    if not question.strip():
        await ctx.send(
            f"{personality_cfg['emoji']} Ask me something real, not just empty air."
        )
        return

    # Send initial response
    processing_msg = await ctx.send(
        f"{personality_cfg['emoji']} *{BOT_PERSONALITY} is contemplating...*"
    )

    # Prepare message for SQS
    message_data = {
        "type": "roast_request",
        "bot_name": BOT_PERSONALITY,
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
    else:
        await processing_msg.edit(
            content=f"{personality_cfg['emoji']} My brain temporarily disconnected. Try again!"
        )


@bot.command(name="status")
async def status(ctx):
    """Check bot status"""
    uptime = datetime.utcnow() - bot.start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)

    embed = discord.Embed(
        title=f"{personality_cfg['emoji']} {BOT_PERSONALITY} Status",
        color=personality_cfg["color"],
    )
    embed.add_field(name="Uptime", value=f"{hours}h {minutes}m {seconds}s", inline=True)
    embed.add_field(name="Roasts Delivered", value=bot.message_count, inline=True)
    embed.add_field(name="Errors", value=bot.error_count, inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.set_footer(text=f"Personality: {BOT_PERSONALITY}")

    await ctx.send(embed=embed)
    put_metric("StatusCommand", 1)


@bot.command(name="help")
async def help_command(ctx):
    """Show bot-specific help"""
    embed = discord.Embed(
        title=f"{personality_cfg['emoji']} {BOT_PERSONALITY} Commands",
        description=f"I'm {BOT_PERSONALITY}, and here's what I can do:",
        color=personality_cfg["color"],
    )

    commands_list = [
        (f"{personality_cfg['prefix']} roast [target]", "Get a personalized roast"),
        (
            f"{personality_cfg['prefix']} ask [question]",
            "Ask me anything for a witty response",
        ),
        (f"{personality_cfg['prefix']} status", "Check my current status"),
        (f"{personality_cfg['prefix']} help", "Show this help message"),
        (f"@{BOT_PERSONALITY} [message]", "Mention me for a response"),
    ]

    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)

    embed.set_footer(text=f"I am {BOT_PERSONALITY}, fear my wit!")
    await ctx.send(embed=embed)
    put_metric("HelpCommand", 1)


# Health check server for ECS
class SimpleHealthServer:
    def __init__(self, discord_bot):
        self.discord_bot = discord_bot
        self.app = web.Application()
        self.app.router.add_get("/health", self.health_check)
        self.runner = None

    async def health_check(self, request):
        """Health check endpoint for ECS"""
        if self.discord_bot.is_ready():
            return web.Response(text="OK", status=200)
        else:
            return web.Response(text="Bot not ready", status=503)

    def start(self):
        """Start health check server"""
        asyncio.create_task(self._run())

    async def _run(self):
        """Run the health check server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "0.0.0.0", 8080)
        await site.start()
        logger.info("Health check server started on port 8080")

    async def stop(self):
        """Stop health check server"""
        if self.runner:
            await self.runner.cleanup()


async def main():
    """Main function to run the bot"""
    health_server = SimpleHealthServer(bot)
    health_server.start()

    try:
        # Start the bot
        await bot.start(DISCORD_TOKEN)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        put_metric("BotCrash", 1)
    finally:
        await health_server.stop()
        await bot.close()


if __name__ == "__main__":
    # Validate environment
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set in environment")
        exit(1)

    if not SQS_QUEUE_URL:
        logger.warning("SQS_QUEUE_URL not set - bot will run without SQS integration")
        # Don't exit - let bot run without SQS

    logger.info(
        f"Starting {BOT_PERSONALITY} with token ending in ...{DISCORD_TOKEN[-6:]}"
    )

    # Run the bot
    asyncio.run(main())
