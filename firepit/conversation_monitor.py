"""Main conversation monitor for Firepit Discord integration"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import discord

from .thread_health import HealthCalculator, ThreadHealthState
from .decision_engine import DecisionEngine, ReplyTypeSelector
from .reply_generator import ReplyGenerator

logger = logging.getLogger(__name__)

class FirepitConversationMonitor:
    """Monitors Discord conversations and enables autonomous bot participation"""
    
    def __init__(self, bot: discord.Client, bot_name: str):
        self.bot = bot
        self.bot_name = bot_name
        self.scan_interval = 5  # seconds
        self.message_cache = {}  # channel_id -> List[message_dict]
        self.last_bot_messages = {}  # channel_id -> datetime
        
        # Initialize components
        self.health_calculator = HealthCalculator()
        self.decision_engine = DecisionEngine(bot_name)
        self.reply_selector = ReplyTypeSelector(bot_name)
        self.reply_generator = ReplyGenerator(bot_name)
        
        self._running = False
        self._monitor_task = None
        
    async def start_monitoring(self):
        """Start the conversation monitoring loop"""
        if self._running:
            return
            
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Firepit monitor started for {self.bot_name}")
        
    async def stop_monitoring(self):
        """Stop the conversation monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            
    async def _monitor_loop(self):
        """Main monitoring loop that runs every 5 seconds"""
        while self._running:
            try:
                # Monitor all active channels
                for guild in self.bot.guilds:
                    for channel in guild.text_channels:
                        # Skip channels we can't read
                        if not channel.permissions_for(guild.me).read_messages:
                            continue
                            
                        await self._check_channel(channel)
                        
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                
            await asyncio.sleep(self.scan_interval)
            
    async def _check_channel(self, channel: discord.TextChannel):
        """Check a single channel for conversation activity"""
        try:
            # Get recent messages
            messages = []
            async for msg in channel.history(limit=20):
                messages.append(self._message_to_dict(msg))
            messages.reverse()  # Oldest first
            
            if not messages:
                return
                
            # Update cache
            self.message_cache[channel.id] = messages
            
            # Calculate health state
            health_state = self.health_calculator.calculate_health(messages)
            
            # Decide if we should speak
            last_bot_msg = self.last_bot_messages.get(channel.id)
            should_speak = self.decision_engine.should_speak(
                health_state, messages, last_bot_msg
            )
            
            if should_speak:
                await self._generate_and_send_reply(channel, health_state, messages)
                
        except Exception as e:
            logger.error(f"Error checking channel {channel.name}: {e}")
            
    async def _generate_and_send_reply(self, channel: discord.TextChannel, 
                                     health_state: ThreadHealthState,
                                     messages: List[Dict]):
        """Generate and send an appropriate reply"""
        try:
            # Select reply type
            reply_type = self.reply_selector.select_reply_type(health_state, messages)
            
            # Build context for generation
            context = {
                'target': self._find_roast_target(messages, health_state),
                'topic': self._extract_current_topic(messages),
                'callback_ref': self._find_callback_reference(messages),
                'health_state': health_state
            }
            
            # Generate reply
            reply = self.reply_generator.generate_reply(reply_type, context)
            
            # Send with typing indicator
            async with channel.typing():
                # Add realistic typing delay
                delay = min(len(reply) * 0.05, 3.0)  # ~20 chars/second, max 3s
                await asyncio.sleep(delay)
                
                await channel.send(reply)
                
            # Update last message time
            self.last_bot_messages[channel.id] = datetime.now(timezone.utc)
            
            logger.info(f"{self.bot_name} sent {reply_type} in {channel.name}")
            
        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            
    def _message_to_dict(self, msg: discord.Message) -> Dict:
        """Convert Discord message to dict format"""
        # Ensure timestamp is timezone-aware
        timestamp = msg.created_at
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            
        return {
            'message_id': str(msg.id),
            'channel_id': str(msg.channel.id),
            'author_id': str(msg.author.id),
            'author_name': msg.author.name,
            'content': msg.content,
            'timestamp': timestamp.isoformat(),
            'is_bot': msg.author.bot,
            'mentions': [m.name for m in msg.mentions],
            'reference': str(msg.reference.message_id) if msg.reference else None
        }
        
    def _find_roast_target(self, messages: List[Dict], health_state: ThreadHealthState) -> str:
        """Find appropriate roast target"""
        # First check if someone needs roasting based on recent activity
        recent_speakers = {}
        for msg in messages[-10:]:
            if not msg['is_bot']:
                author = msg['author_name']
                recent_speakers[author] = recent_speakers.get(author, 0) + 1
                
        # Roast the loudest non-bot
        if recent_speakers:
            return max(recent_speakers, key=recent_speakers.get)
            
        # Fall back to last roast target or generic
        return health_state.last_roast_target or "y'all"
        
    def _extract_current_topic(self, messages: List[Dict]) -> str:
        """Extract current conversation topic"""
        # Simple: look for nouns in recent messages
        recent_content = ' '.join(msg['content'] for msg in messages[-5:])
        
        # Basic topic extraction (could be enhanced with NLP)
        topics = []
        for word in recent_content.split():
            if len(word) > 4 and word[0].isupper():
                topics.append(word)
                
        return topics[0] if topics else "this whole situation"
        
    def _find_callback_reference(self, messages: List[Dict]) -> str:
        """Find something to callback to"""
        # Look for memorable moments (messages with lots of reactions/replies)
        for msg in messages[:-5]:  # Not too recent
            if len(msg.get('mentions', [])) > 1 or '!' in msg['content']:
                # Extract key phrase
                words = msg['content'].split()
                if len(words) > 3:
                    return ' '.join(words[:4]) + "..."
                    
        return "that thing from before"
        
    async def on_message(self, message: discord.Message):
        """Handle incoming messages (for immediate context)"""
        # Update cache immediately when messages come in
        if message.channel.id in self.message_cache:
            self.message_cache[message.channel.id].append(self._message_to_dict(message))
            # Keep only last 20
            self.message_cache[message.channel.id] = self.message_cache[message.channel.id][-20:]