"""Thread health state monitoring for Firepit Discord Agent"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class ThreadHealthState:
    """Current state of conversation health"""
    dead_air_seconds: int = 0
    heat_score: float = 0.0
    last_roast_target: Optional[str] = None
    quiet_bot: Optional[str] = None
    dominant_speaker: Optional[str] = None
    message_type_ratios: Dict[str, float] = None
    last_pivot_timestamp: Optional[datetime] = None
    current_topic: Optional[str] = None
    topic_message_count: int = 0
    
    def __post_init__(self):
        if self.message_type_ratios is None:
            self.message_type_ratios = {
                "roast": 0.0,
                "riff": 0.0,
                "story": 0.0,
                "pivot": 0.0
            }

class HealthCalculator:
    """Calculates conversation health metrics"""
    
    def __init__(self):
        self.message_window = 20  # Last 20 messages
        self.heat_decay_rate = 0.1  # Heat decays over time
        
    def calculate_health(self, messages: List[Dict]) -> ThreadHealthState:
        """Calculate current conversation health from message history"""
        if not messages:
            return ThreadHealthState()
            
        now = datetime.now(timezone.utc)
        recent_messages = messages[-self.message_window:]
        
        # Calculate dead air
        if recent_messages:
            last_msg_time = datetime.fromisoformat(recent_messages[-1]['timestamp'].replace('Z', '+00:00'))
            dead_air_seconds = int((now - last_msg_time).total_seconds())
        else:
            dead_air_seconds = 999
            
        # Calculate heat score (0-10 scale)
        heat_score = self._calculate_heat_score(recent_messages)
        
        # Find quiet bot and dominant speaker
        speaker_counts = {}
        bot_counts = {}
        
        for msg in recent_messages:
            author = msg['author_name']
            speaker_counts[author] = speaker_counts.get(author, 0) + 1
            
            if msg.get('is_bot'):
                bot_counts[author] = bot_counts.get(author, 0) + 1
                
        # Dominant speaker is whoever has most messages
        if speaker_counts:
            dominant_speaker = max(speaker_counts, key=speaker_counts.get)
        else:
            dominant_speaker = None
            
        # Quiet bot is the bot with least messages (including 0)
        all_bots = ['FordBot', 'AprilBot', 'AdamBot']
        quiet_bot = None
        min_count = float('inf')
        
        for bot in all_bots:
            count = bot_counts.get(bot, 0)
            if count < min_count:
                min_count = count
                quiet_bot = bot
                
        # Get last roast target
        last_roast_target = self._find_last_roast_target(recent_messages)
        
        # Calculate message type ratios
        message_type_ratios = self._calculate_message_ratios(recent_messages)
        
        # Find last pivot
        last_pivot_timestamp = self._find_last_pivot(recent_messages)
        
        # Track current topic
        current_topic, topic_message_count = self._track_current_topic(recent_messages)
        
        return ThreadHealthState(
            dead_air_seconds=dead_air_seconds,
            heat_score=heat_score,
            last_roast_target=last_roast_target,
            quiet_bot=quiet_bot,
            dominant_speaker=dominant_speaker,
            message_type_ratios=message_type_ratios,
            last_pivot_timestamp=last_pivot_timestamp,
            current_topic=current_topic,
            topic_message_count=topic_message_count
        )
        
    def _calculate_heat_score(self, messages: List[Dict]) -> float:
        """Calculate conversation heat (0-10)"""
        if not messages:
            return 0.0
            
        heat = 0.0
        now = datetime.now(timezone.utc)
        
        for msg in messages:
            msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
            age_minutes = (now - msg_time).total_seconds() / 60
            
            # Base heat from message
            msg_heat = 1.0
            
            # Boost for roasts
            if 'roast' in msg.get('content', '').lower():
                msg_heat += 2.0
                
            # Boost for mentions
            if msg.get('mentions'):
                msg_heat += 1.0
                
            # Boost for emojis
            emoji_count = len([c for c in msg.get('content', '') if ord(c) > 127462])
            msg_heat += emoji_count * 0.5
            
            # Apply time decay
            decay_factor = max(0, 1 - (age_minutes * self.heat_decay_rate))
            heat += msg_heat * decay_factor
            
        # Normalize to 0-10 scale
        return min(10.0, heat / 2)
        
    def _find_last_roast_target(self, messages: List[Dict]) -> Optional[str]:
        """Find who was last roasted"""
        for msg in reversed(messages):
            if 'roast' in msg.get('content', '').lower():
                # Simple heuristic: look for mentions
                if msg.get('mentions'):
                    return msg['mentions'][0]
        return None
        
    def _calculate_message_ratios(self, messages: List[Dict]) -> Dict[str, float]:
        """Calculate ratios of different message types"""
        if not messages:
            return {"roast": 0.0, "riff": 0.0, "story": 0.0, "pivot": 0.0}
            
        counts = {"roast": 0, "riff": 0, "story": 0, "pivot": 0}
        
        for msg in messages:
            content = msg.get('content', '').lower()
            
            # Simple classification
            if 'roast' in content or any(word in content for word in ['trash', 'weak', 'L', 'ratio']):
                counts['roast'] += 1
            elif len(content) > 200:
                counts['story'] += 1
            elif '?' in content or 'what if' in content:
                counts['pivot'] += 1
            else:
                counts['riff'] += 1
                
        total = len(messages)
        return {k: v/total for k, v in counts.items()}
        
    def _find_last_pivot(self, messages: List[Dict]) -> Optional[datetime]:
        """Find when conversation last pivoted topics"""
        for msg in reversed(messages):
            content = msg.get('content', '').lower()
            if any(phrase in content for phrase in ['what if', 'actually', 'real talk', 'anyway']):
                return datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
        return None
        
    def _track_current_topic(self, messages: List[Dict]) -> tuple[Optional[str], int]:
        """Track the current topic and how many messages have discussed it"""
        if not messages:
            return None, 0
            
        # Simple topic extraction - look for recurring themes/words
        topic_words = {}
        
        # Look at last 10 messages
        for msg in messages[-10:]:
            content = msg.get('content', '').lower()
            # Extract meaningful words (simple approach)
            words = [w for w in content.split() if len(w) > 4 and not w.startswith('http')]
            for word in words:
                topic_words[word] = topic_words.get(word, 0) + 1
                
        # Find most common topic word
        if topic_words:
            current_topic = max(topic_words, key=topic_words.get)
            topic_count = topic_words[current_topic]
            return current_topic, topic_count
            
        return None, 0