#!/usr/bin/env python3
"""
Conversation monitoring and autonomous reply system for AI Roast Den bots
"""
import os
import json
import time
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import boto3
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Represents a message in the conversation"""

    message_id: str
    channel_id: str
    author_id: str
    author_name: str
    content: str
    timestamp: datetime
    is_bot: bool
    bot_name: Optional[str] = None
    mentions: List[str] = None
    reply_to: Optional[str] = None


@dataclass
class ConversationState:
    """Tracks the state of a conversation in a channel"""

    channel_id: str
    messages: List[Message]
    last_bot_replies: Dict[str, datetime]  # bot_name -> last_reply_time
    bot_reply_counts: Dict[str, int]  # bot_name -> replies in last hour
    conversation_energy: float  # 0-1 scale of how active/heated
    dominant_topics: List[str]


class ConversationAnalyzer:
    """Analyzes conversations and decides if a bot should reply"""

    def __init__(self, bot_name: str, rules_file: str = "conversation_rules.json"):
        self.bot_name = bot_name
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

        # Load conversation rules
        with open(rules_file, "r") as f:
            self.rules = json.load(f)

        self.hard_rules = self.rules["hard_rules"]
        self.vibe_rules = self.rules["vibe_rules"][bot_name]
        self.interaction_dynamics = self.rules["interaction_dynamics"]
        self.special_triggers = self.rules["special_triggers"]

    def check_hard_rules(self, state: ConversationState) -> Tuple[bool, Optional[str]]:
        """Check if hard rules allow this bot to reply"""

        # Rule 1: No double reply
        if state.messages and state.messages[-1].bot_name == self.bot_name:
            return False, "Cannot reply to myself"

        # Rule 2: Wait for response if directly addressed someone
        if len(state.messages) >= 2:
            last_bot_msg = None
            for msg in reversed(state.messages):
                if msg.bot_name == self.bot_name:
                    last_bot_msg = msg
                    break

            if last_bot_msg and last_bot_msg.mentions:
                # Check if any of the mentioned bots have replied
                mentioned_bots = [m for m in last_bot_msg.mentions if m.endswith("Bot")]
                if mentioned_bots:
                    replied = False
                    for msg in state.messages[state.messages.index(last_bot_msg) + 1 :]:
                        if msg.bot_name in mentioned_bots:
                            replied = True
                            break
                    if not replied:
                        return False, f"Waiting for response from {mentioned_bots}"

        # Rule 3: Cooldown period
        last_reply = state.last_bot_replies.get(self.bot_name)
        if last_reply:
            cooldown = self.hard_rules["cooldown_period"]["seconds"]
            if (datetime.utcnow() - last_reply).total_seconds() < cooldown:
                return False, f"In cooldown period ({cooldown}s)"

        # Rule 4: Rate limit
        hourly_limit = self.hard_rules["max_replies_per_hour"]["limit"]
        if state.bot_reply_counts.get(self.bot_name, 0) >= hourly_limit:
            return False, f"Reached hourly limit ({hourly_limit})"

        return True, None

    def calculate_reply_probability(
        self, state: ConversationState, message: Message
    ) -> float:
        """Calculate probability this bot should reply based on vibes"""

        # Start with base probability
        probability = self.vibe_rules["reply_probability_base"]

        # Apply personality modifiers
        modifiers = self.vibe_rules["personality_modifiers"]

        # Check if mentioned
        if self.bot_name in (message.mentions or []):
            probability += modifiers.get("when_mentioned", 0)

        # Check if roasted
        if any(
            word in message.content.lower() for word in ["roast", "burn", "destroyed"]
        ):
            probability += modifiers.get("when_roasted", 0)

        # Check conversation energy
        if state.conversation_energy > 0.7:
            probability += modifiers.get("conversation_getting_heated", 0)
        elif state.conversation_energy < 0.3:
            probability += modifiers.get("when_energy_low", 0)

        # Check time since last reply
        last_reply = state.last_bot_replies.get(self.bot_name)
        if last_reply:
            minutes_quiet = (datetime.utcnow() - last_reply).total_seconds() / 60
            if minutes_quiet > 10:
                probability += modifiers.get("been_quiet_for_10min", 0)
            elif minutes_quiet < 2:
                probability += modifiers.get("just_replied", 0)

        # Bot-specific checks
        if self.bot_name == "FordBot":
            if any(
                word in message.content.lower()
                for word in ["meaning", "philosophy", "wisdom", "life"]
            ):
                probability += modifiers.get("when_philosophy_discussed", 0)

        elif self.bot_name == "AprilBot":
            # Check if conversation needs chaos
            if self._is_conversation_orderly(state):
                probability += modifiers.get("conversation_too_orderly", 0)

            # React to Ford being philosophical
            if state.messages and state.messages[-1].bot_name == "FordBot":
                if any(
                    word in state.messages[-1].content.lower()
                    for word in ["wisdom", "truth", "meaning"]
                ):
                    probability += modifiers.get("after_ford_philosophical", 0)

        elif self.bot_name == "AdamBot":
            # Check for music references
            if any(
                word in message.content.lower()
                for word in ["music", "beat", "rhythm", "song", "drum"]
            ):
                probability += modifiers.get("when_music_discussed", 0)

            # Check for good timing
            if self._is_good_timing(state):
                probability += modifiers.get("when_timing_is_perfect", 0)

        # Apply special triggers
        for trigger_name, trigger in self.special_triggers.items():
            if self._check_trigger(message, trigger):
                boost_key = f"{self.bot_name.lower()}_boost"
                if boost_key in trigger:
                    probability += trigger[boost_key]
                elif "probability_boost" in trigger:
                    probability += trigger["probability_boost"]

        # Apply interaction dynamics
        if state.messages:
            last_bot = state.messages[-1].bot_name
            if last_bot and last_bot != self.bot_name:
                interaction_key = "_".join(
                    sorted(
                        [
                            self.bot_name.lower().replace("bot", ""),
                            last_bot.lower().replace("bot", ""),
                        ]
                    )
                )
                if interaction_key in self.interaction_dynamics:
                    dynamics = self.interaction_dynamics[interaction_key]
                    boost_key = f"{self.bot_name.lower()}_response_boost"
                    if boost_key in dynamics:
                        probability += dynamics[boost_key]

        # Clamp probability between 0 and 1
        return max(0, min(1, probability))

    def _is_conversation_orderly(self, state: ConversationState) -> bool:
        """Check if conversation is too orderly (needs April's chaos)"""
        if len(state.messages) < 5:
            return False

        # Check for back-and-forth pattern
        authors = [msg.author_name for msg in state.messages[-5:]]
        unique_authors = len(set(authors))

        # Too orderly if just 2 people talking back and forth
        return unique_authors == 2 and authors[0] != authors[1]

    def _is_good_timing(self, state: ConversationState) -> bool:
        """Check if it's good timing for Adam to drop in"""
        if len(state.messages) < 3:
            return False

        # Good timing after a setup
        last_msg = state.messages[-1]
        if last_msg.content.endswith("?") or any(
            word in last_msg.content.lower() for word in ["setup", "but", "however"]
        ):
            return True

        # Good timing for a punchline
        if state.conversation_energy > 0.5 and len(state.messages[-1].content) < 100:
            return True

        return False

    def _check_trigger(self, message: Message, trigger: Dict) -> bool:
        """Check if a special trigger is activated"""
        if "keywords" in trigger:
            return any(
                keyword in message.content.lower() for keyword in trigger["keywords"]
            )
        elif "description" in trigger:
            # For complex triggers, could use Claude to evaluate
            return trigger["description"].lower() in message.content.lower()
        return False

    async def should_reply(
        self, channel_id: str, new_message: Message
    ) -> Tuple[bool, float, str]:
        """
        Determine if bot should reply to a message
        Returns: (should_reply, probability, reason)
        """
        # Get conversation state
        state = await self.get_conversation_state(channel_id)

        # Add new message to state
        state.messages.append(new_message)

        # Check hard rules first
        can_reply, block_reason = self.check_hard_rules(state)
        if not can_reply:
            return False, 0.0, block_reason

        # Calculate reply probability based on vibes
        probability = self.calculate_reply_probability(state, new_message)

        # Use Claude for complex decision making
        if probability > 0.3:  # Only ask Claude if there's decent chance
            claude_opinion = await self.get_claude_opinion(
                state, new_message, probability
            )
            # Claude can modify probability by up to 30%
            probability = probability * 0.7 + claude_opinion * 0.3

        # Make final decision
        import random

        should_reply = random.random() < probability

        reason = (
            f"Probability: {probability:.2f}, Energy: {state.conversation_energy:.2f}"
        )
        if should_reply:
            reason += f", {self.vibe_rules['conversation_style']}"

        return should_reply, probability, reason

    async def get_conversation_state(self, channel_id: str) -> ConversationState:
        """Get current conversation state from DynamoDB"""
        # This would fetch from DynamoDB in production
        # For now, return a mock state
        return ConversationState(
            channel_id=channel_id,
            messages=[],
            last_bot_replies={},
            bot_reply_counts=defaultdict(int),
            conversation_energy=0.5,
            dominant_topics=[],
        )

    async def get_claude_opinion(
        self, state: ConversationState, new_message: Message, current_probability: float
    ) -> float:
        """Ask Claude if the bot should reply given the conversation context"""

        # Build conversation context
        context = self._build_conversation_context(state, new_message)

        prompt = f"""You are helping {self.bot_name} decide whether to reply to a message.

Bot Personality: {self.vibe_rules['conversation_style']}
Current reply probability: {current_probability:.2f}

Recent conversation:
{context}

New message from {new_message.author_name}: "{new_message.content}"

Based on {self.bot_name}'s personality and the conversation flow, should they reply?
Consider:
- Is it good timing for {self.bot_name} to jump in?
- Would their response add value or humor?
- Does the conversation need their specific energy?

Respond with just a probability between 0 and 1."""

        try:
            response = self.bedrock.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(
                    {
                        "messages": [{"role": "user", "content": prompt}],
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 10,
                        "temperature": 0.7,
                    }
                ),
            )
            result = json.loads(response["body"].read())
            probability_str = result["content"][0]["text"].strip()
            return float(probability_str)
        except Exception as e:
            logger.error(f"Claude opinion error: {e}")
            return current_probability

    def _build_conversation_context(
        self, state: ConversationState, new_message: Message
    ) -> str:
        """Build a readable conversation context"""
        context_lines = []
        for msg in state.messages[-10:]:  # Last 10 messages
            author = msg.bot_name if msg.is_bot else msg.author_name
            context_lines.append(f"{author}: {msg.content}")
        return "\n".join(context_lines)


class ConversationMonitor:
    """Monitors Discord channels and triggers autonomous bot replies"""

    def __init__(self, bot_client, bot_name: str):
        self.bot = bot_client
        self.bot_name = bot_name
        self.analyzer = ConversationAnalyzer(bot_name)
        self.monitored_channels = set()

    async def start_monitoring(self):
        """Start monitoring conversations"""
        logger.info(f"{self.bot_name} conversation monitor started")

        # Monitor all channels the bot can see
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).read_messages:
                    self.monitored_channels.add(channel.id)

        logger.info(f"Monitoring {len(self.monitored_channels)} channels")

    async def on_message(self, message):
        """Process new messages and decide whether to reply"""
        # Skip if not in monitored channel
        if message.channel.id not in self.monitored_channels:
            return

        # Skip own messages
        if message.author.id == self.bot.user.id:
            return

        # Create Message object
        msg = Message(
            message_id=str(message.id),
            channel_id=str(message.channel.id),
            author_id=str(message.author.id),
            author_name=message.author.name,
            content=message.content,
            timestamp=message.created_at,
            is_bot=message.author.bot,
            bot_name=(
                self._extract_bot_name(message.author) if message.author.bot else None
            ),
            mentions=[user.name for user in message.mentions],
        )

        # Decide if we should reply
        should_reply, probability, reason = await self.analyzer.should_reply(
            str(message.channel.id), msg
        )

        logger.info(f"{self.bot_name} reply decision: {should_reply} ({reason})")

        if should_reply:
            await self.send_autonomous_reply(message, reason)

    async def send_autonomous_reply(self, original_message, reason: str):
        """Send an autonomous reply to the conversation"""
        # Add typing indicator for realism
        async with original_message.channel.typing():
            # Wait 1-3 seconds to seem more natural
            import random

            await asyncio.sleep(random.uniform(1, 3))

            # Send message to SQS for processing
            from bot_container_personality import send_to_sqs

            message_data = {
                "type": "autonomous_reply",
                "bot_name": self.bot_name,
                "channel_id": str(original_message.channel.id),
                "message_id": None,  # Will create new message
                "context_message_id": str(original_message.id),
                "user_id": str(original_message.author.id),
                "user_name": original_message.author.name,
                "question": original_message.content,
                "reply_reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # For now, send a placeholder while Lambda processes
            thinking_msgs = {
                "FordBot": "🧘‍♂️ *contemplates the void*",
                "AprilBot": "🎪 *spins plates menacingly*",
                "AdamBot": "🥁 *taps fingers rhythmically*",
            }

            msg = await original_message.channel.send(
                thinking_msgs.get(self.bot_name, "🤔 *thinking*")
            )
            message_data["message_id"] = str(msg.id)

            if send_to_sqs(message_data):
                logger.info(f"{self.bot_name} sent autonomous reply to SQS")
            else:
                await msg.edit(content="*decides to stay quiet*")

    def _extract_bot_name(self, user) -> Optional[str]:
        """Extract bot name from Discord user"""
        # Match our bot naming convention
        if user.name in ["FordBot", "AprilBot", "AdamBot"]:
            return user.name
        return None
