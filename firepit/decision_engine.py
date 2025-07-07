"""Decision engine for bot participation in conversations"""
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging

from .thread_health import ThreadHealthState

logger = logging.getLogger(__name__)

class DecisionEngine:
    """Decides when and how bots should participate"""
    
    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.user_deference_turns = 6  # Doubled: Pause after human speaks
        self.max_quiet_turns = 20  # Doubled: Speak if quiet for this many turns
        self.jitter_factor = 0.2  # Random variation
        
    def should_speak(self, health_state: ThreadHealthState, 
                    recent_messages: List[Dict],
                    last_bot_message_time: Optional[datetime]) -> bool:
        """Determine if this bot should speak now"""
        
        # Check quiet hours first (8pm-8am EST)
        now = datetime.now(timezone.utc)
        est_hour = (now.hour - 5) % 24  # Convert to EST (UTC-5)
        if est_hour >= 20 or est_hour < 8:  # 8pm to 8am
            logger.debug(f"{self.bot_name}: Quiet hours - no speaking")
            return False
            
        # Check dead air first - override user deference if it's been too long
        if health_state.dead_air_seconds > 60:  # Doubled: 60 seconds before override
            logger.debug(f"{self.bot_name}: Dead air override - {health_state.dead_air_seconds}s")
            if self._should_break_silence(health_state):
                return True
        
        # Check if user spoke recently (defer)
        if self._user_spoke_recently(recent_messages):
            logger.debug(f"{self.bot_name}: Deferring to user")
            return False
            
        # Check if we're the quiet bot who needs to speak
        if health_state.quiet_bot == self.bot_name:
            quiet_score = self._calculate_quiet_urgency(recent_messages)
            if quiet_score > 0.7:
                logger.debug(f"{self.bot_name}: Speaking as quiet bot")
                return True
                
        # Check dead air
        if health_state.dead_air_seconds > 8:  # Doubled: 8 seconds instead of 4
            if self._should_break_silence(health_state):
                logger.debug(f"{self.bot_name}: Breaking silence")
                return True
                
        # Check low heat
        if health_state.heat_score < 5:
            if self._should_escalate_heat(health_state):
                logger.debug(f"{self.bot_name}: Escalating heat")
                return True
                
        # Check if we're dominating (back off)
        if health_state.dominant_speaker == self.bot_name:
            logger.debug(f"{self.bot_name}: Backing off as dominant")
            return False
            
        # Random participation with jitter
        base_probability = self._calculate_base_probability(health_state)
        jittered_prob = base_probability * (1 + random.uniform(-self.jitter_factor, self.jitter_factor))
        
        return random.random() < jittered_prob
        
    def _user_spoke_recently(self, recent_messages: List[Dict]) -> bool:
        """Check if human spoke in last few messages"""
        if not recent_messages:
            return False
            
        # Look at last 3 messages
        for msg in recent_messages[-self.user_deference_turns:]:
            if not msg.get('is_bot', False):
                return True
        return False
        
    def _calculate_quiet_urgency(self, recent_messages: List[Dict]) -> float:
        """Calculate urgency for quiet bot to speak (0-1)"""
        if not recent_messages:
            return 1.0
            
        # Count turns since we last spoke
        turns_quiet = 0
        for msg in reversed(recent_messages):
            if msg.get('author_name') == self.bot_name:
                break
            turns_quiet += 1
            
        # Convert to urgency score
        urgency = min(1.0, turns_quiet / self.max_quiet_turns)
        return urgency
        
    def _should_break_silence(self, health_state: ThreadHealthState) -> bool:
        """Decide if we should break dead air"""
        # Higher chance if we're not dominant speaker
        if health_state.dominant_speaker == self.bot_name:
            return random.random() < 0.2
            
        # Higher chance if we're the quiet bot
        if health_state.quiet_bot == self.bot_name:
            return random.random() < 0.8
            
        # Normal chance
        return random.random() < 0.5
        
    def _should_escalate_heat(self, health_state: ThreadHealthState) -> bool:
        """Decide if we should escalate conversation heat"""
        # Bot-specific escalation preferences
        escalation_prefs = {
            'AprilBot': 0.8,   # April loves to escalate
            'FordBot': 0.5,    # Ford is balanced
            'AdamBot': 0.3     # Adam is more reserved
        }
        
        base_chance = escalation_prefs.get(self.bot_name, 0.5)
        
        # Increase chance if heat is very low
        if health_state.heat_score < 3:
            base_chance *= 1.5
            
        return random.random() < min(1.0, base_chance)
        
    def _calculate_base_probability(self, health_state: ThreadHealthState) -> float:
        """Calculate base probability of speaking"""
        # Start with bot personality base - halved for less noise
        base_probs = {
            'FordBot': 0.075,   # Was 0.15
            'AprilBot': 0.05,   # Was 0.10
            'AdamBot': 0.06     # Was 0.12
        }
        
        prob = base_probs.get(self.bot_name, 0.05)
        
        # Adjust based on conversation state
        if health_state.heat_score > 7:
            prob *= 1.2  # More active in hot convos
        elif health_state.heat_score < 3:
            prob *= 0.8  # Less active in cold convos
            
        return min(0.15, prob)  # Cap at 15% base (was 30%)

class ReplyTypeSelector:
    """Selects appropriate reply type based on context"""
    
    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.roast_quota = 3  # Max roasts in a row
        
    def select_reply_type(self, health_state: ThreadHealthState,
                         recent_messages: List[Dict]) -> str:
        """Select type of reply to generate"""
        
        # Check roast quota
        recent_roasts = self._count_recent_roasts_to_target(
            recent_messages, 
            health_state.last_roast_target
        )
        
        if recent_roasts >= self.roast_quota:
            # Must do something other than roast
            return self._select_non_roast_type(health_state)
            
        # Check for callback opportunity
        if self._should_callback(recent_messages):
            return "callback"
            
        # Check for tone reset need
        if self._needs_tone_reset(health_state):
            return "pivot"
            
        # Normal selection based on conversation state
        return self._select_by_state(health_state)
        
    def _count_recent_roasts_to_target(self, messages: List[Dict], target: Optional[str]) -> int:
        """Count recent roasts toward same target"""
        if not target:
            return 0
            
        count = 0
        for msg in reversed(messages):
            if msg.get('author_name') == self.bot_name:
                if 'roast' in msg.get('content', '').lower() and target in msg.get('content', ''):
                    count += 1
                else:
                    break
        return count
        
    def _should_callback(self, messages: List[Dict]) -> bool:
        """Check if callback would be good"""
        now = datetime.now(timezone.utc)
        
        # Look for callback opportunities (15+ min old references)
        for msg in messages[:-5]:  # Not too recent
            msg_time = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
            if (now - msg_time).total_seconds() > 900:  # 15 minutes
                if random.random() < 0.2:  # 20% chance
                    return True
        return False
        
    def _needs_tone_reset(self, health_state: ThreadHealthState) -> bool:
        """Check if conversation needs tone reset"""
        # Check topic coherence first - need 3 exchanges minimum
        if health_state.topic_message_count < 6:  # 3 exchanges = ~6 messages
            return False  # Don't pivot yet
            
        # Too much roasting
        if health_state.message_type_ratios.get('roast', 0) > 0.6:
            return True
            
        # Too quiet/boring
        if health_state.heat_score < 2:
            return True
            
        # Been too long since pivot
        if health_state.last_pivot_timestamp:
            mins_since_pivot = (datetime.now(timezone.utc) - health_state.last_pivot_timestamp).total_seconds() / 60
            if mins_since_pivot > 30:
                return True
                
        return False
        
    def _select_non_roast_type(self, health_state: ThreadHealthState) -> str:
        """Select reply type when roasting is off limits"""
        # Temporarily remove story for AprilBot due to generation issues
        if self.bot_name == 'AprilBot':
            options = ['riff', 'pivot', 'praise']
        else:
            options = ['riff', 'story', 'pivot', 'praise']
        
        # Weight based on what's needed
        if health_state.heat_score < 3:
            return 'pivot'  # Change topic
        elif health_state.message_type_ratios.get('story', 0) < 0.1 and self.bot_name != 'AprilBot':
            return 'story'  # Add depth
        else:
            return random.choice(options)
            
    def _select_by_state(self, health_state: ThreadHealthState) -> str:
        """Normal reply type selection"""
        # Bot personality preferences
        preferences = {
            'AprilBot': {'roast': 0.4, 'riff': 0.4, 'callback': 0.15, 'pivot': 0.05},  # No story for now
            'AdamBot': {'riff': 0.3, 'story': 0.3, 'roast': 0.2, 'pivot': 0.2},
            'FordBot': {'story': 0.3, 'pivot': 0.3, 'roast': 0.2, 'riff': 0.2}
        }
        
        bot_prefs = preferences.get(self.bot_name, {
            'roast': 0.25, 'riff': 0.25, 'story': 0.25, 'pivot': 0.25
        })
        
        # Adjust based on conversation needs
        adjusted_prefs = bot_prefs.copy()
        
        if health_state.heat_score < 5:
            adjusted_prefs['roast'] *= 1.5
        if health_state.message_type_ratios.get('story', 0) < 0.2:
            adjusted_prefs['story'] *= 1.3
            
        # Normalize and select
        total = sum(adjusted_prefs.values())
        normalized = {k: v/total for k, v in adjusted_prefs.items()}
        
        rand = random.random()
        cumulative = 0
        
        for reply_type, prob in normalized.items():
            cumulative += prob
            if rand < cumulative:
                return reply_type
                
        return 'riff'  # Default