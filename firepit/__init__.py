"""Firepit Discord Agent - Autonomous conversation participation system"""

from .conversation_monitor import FirepitConversationMonitor
from .thread_health import ThreadHealthState, HealthCalculator
from .decision_engine import DecisionEngine, ReplyTypeSelector
from .reply_generator import ReplyGenerator

__all__ = [
    'FirepitConversationMonitor',
    'ThreadHealthState',
    'HealthCalculator',
    'DecisionEngine',
    'ReplyTypeSelector',
    'ReplyGenerator'
]

__version__ = '1.0.0'