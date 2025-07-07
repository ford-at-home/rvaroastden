"""Reply generation for Firepit bots"""
import random
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ReplyGenerator:
    """Generates contextual replies based on bot personality and conversation state"""
    
    def __init__(self, bot_name: str):
        self.bot_name = bot_name
        self.personalities = self._load_personalities()
        
    def generate_reply(self, reply_type: str, context: Dict) -> str:
        """Generate a reply of the specified type"""
        
        generators = {
            'roast': self._generate_roast,
            'riff': self._generate_riff,
            'story': self._generate_story,
            'pivot': self._generate_pivot,
            'callback': self._generate_callback,
            'praise': self._generate_praise
        }
        
        generator = generators.get(reply_type, self._generate_riff)
        try:
            return generator(context)
        except Exception as e:
            logger.error(f"Error in {reply_type} generation for {self.bot_name}: {e}", exc_info=True)
            # Fallback to a simple riff
            return self._generate_riff(context)
        
    def _load_personalities(self) -> Dict:
        """Load bot personality configurations"""
        return {
            'AprilBot': {
                'roast_style': 'fire callbacks and contradictions',
                'emoji_density': 'high',
                'punctuation': '!!!',
                'catchphrases': [
                    'SCREAMING',
                    'I CANNOT',
                    'bestie...',
                    'not you thinking',
                    'the way you just'
                ],
                'roast_templates': [
                    "NOT {target} THINKING THEY DID SOMETHING 💀",
                    "bestie... this ain't it 🔥",
                    "SCREAMING at {target} rn 😭",
                    "the AUDACITY... I have to laugh",
                    "{target} really said that with their whole chest huh"
                ]
            },
            'AdamBot': {
                'roast_style': 'observant strikes with analogies',
                'emoji_density': 'low',
                'punctuation': '.',
                'catchphrases': [
                    'statistically speaking',
                    'from a game theory perspective',
                    'this reminds me of',
                    'actually',
                    'to be fair'
                ],
                'roast_templates': [
                    "Statistically, {target} just achieved a new low.",
                    "This is like watching the 2020 Eagles all over again.",
                    "From a scientific perspective, that was objectively terrible.",
                    "{target}'s take has the structural integrity of wet cardboard.",
                    "Game theory suggests {target} should have stayed quiet."
                ]
            },
            'FordBot': {
                'roast_style': 'philosophical musings to dad jokes',
                'emoji_density': 'medium',
                'punctuation': '...',
                'catchphrases': [
                    'you know what they say',
                    'back in my day',
                    'philosophically speaking',
                    'well now',
                    'let me tell you'
                ],
                'roast_templates': [
                    "You know {target}, you remind me of a project car... lots of potential, zero progress.",
                    "Philosophically speaking, {target}'s existence raises questions... mainly 'why?'",
                    "Back in my day, we had standards. Then {target} showed up.",
                    "Well now, {target} just proved that evolution can go backwards.",
                    "{target}... proof that not all thoughts need to be shared."
                ]
            }
        }
        
    def _generate_roast(self, context: Dict) -> str:
        """Generate a roast based on personality"""
        personality = self.personalities[self.bot_name]
        target = context.get('target', 'this whole situation')
        
        # Pick a template
        template = random.choice(personality['roast_templates'])
        roast = template.format(target=target)
        
        # Add emoji based on density
        if personality['emoji_density'] == 'high':
            roast += ' ' + random.choice(['🔥', '💀', '😭', '✋', '🤡'])
            
        return roast
        
    def _generate_riff(self, context: Dict) -> str:
        """Generate a riff on the current topic"""
        personality = self.personalities[self.bot_name]
        
        riff_starters = {
            'AprilBot': [
                "okay but like",
                "no because",
                "WAIT",
                "the way I just realized",
                "not me thinking about"
            ],
            'AdamBot': [
                "Following up on that",
                "Interesting point about",
                "That actually reminds me",
                "Building on what was said",
                "From another angle"
            ],
            'FordBot': [
                "That reminds me",
                "Speaking of which",
                "You know what's funny",
                "I was just thinking",
                "Here's the thing though"
            ]
        }
        
        starter = random.choice(riff_starters[self.bot_name])
        topic = context.get('topic', 'this whole thing')
        
        return f"{starter} {topic}{personality['punctuation']}"
        
    def _generate_story(self, context: Dict) -> str:
        """Generate a story or longer share"""
        personality = self.personalities[self.bot_name]
        
        story_templates = {
            'AprilBot': [
                "OKAY STORY TIME... so {time_ref} I was {action} and {twist} happened {emoji}",
                "no because this one time {event} and I literally {reaction} {emoji}",
                "wait this reminds me of when {person} tried to {action} and it was a MESS"
            ],
            'AdamBot': [
                "This is exactly like {time_ref} when {technical_thing} happened. {analysis}. {conclusion}.",
                "Reminds me of a case study where {scenario}. The data showed {finding}.",
                "Similar thing happened in {context}. {observation}. {insight}."
            ],
            'FordBot': [
                "Back in {time_ref}, we used to {action}. {nostalgic_observation}. {life_lesson}.",
                "Let me tell you about the time {event}. {philosophical_musing}. {dad_joke}.",
                "You know, {time_ref} I learned that {wisdom}. {rambling_addition}."
            ]
        }
        
        # Select a random template for this bot
        template = random.choice(story_templates.get(self.bot_name, story_templates['FordBot']))
        
        # Bot-specific fills
        if self.bot_name == 'AprilBot':
            story = template.format(
                time_ref=random.choice(['last week', 'yesterday', 'this morning']),
                action=random.choice(['at Target', 'getting coffee', 'scrolling']),
                twist=random.choice(['the WILDEST thing', 'you would not BELIEVE what', 'this person']),
                event='I saw my ex',
                reaction='DIED',
                person='that one friend',
                emoji=random.choice(['💀', '😭', '✋'])
            )
        elif self.bot_name == 'AdamBot':
            story = template.format(
                time_ref=random.choice(['last quarter', 'in 2019', 'during the playoffs']),
                technical_thing='the analytics broke',
                analysis='Pattern recognition suggested anomaly',
                conclusion='Sometimes correlation does imply causation',
                scenario='users exceeded expected parameters',
                finding='inverse correlation',
                context='game 6',
                observation='Defense wins championships',
                insight='But offense sells tickets'
            )
        else:  # FordBot
            story = template.format(
                time_ref=random.choice(['89', 'the old days', 'my youth']),
                action=random.choice(['fix things ourselves', 'talk to people face to face', 'use maps']),
                nostalgic_observation="None of this instant everything",
                life_lesson="Sometimes slower is better",
                event="I tried to modernize",
                philosophical_musing="Technology connects us but divides us",
                dad_joke="Like my wifi - intermittent at best",
                wisdom="the best debugger is a good night's sleep",
                rambling_addition="Course, that was before the cloud"
            )
            
        return story
        
    def _generate_pivot(self, context: Dict) -> str:
        """Generate a topic pivot"""
        personality = self.personalities[self.bot_name]
        
        pivot_templates = {
            'AprilBot': [
                "ANYWAY moving on from that disaster...",
                "okay but real talk though",
                "wait actually important question",
                "CAN WE TALK ABOUT how",
                "not to change the subject but"
            ],
            'AdamBot': [
                "Shifting gears for a moment,",
                "On a different note,",
                "Actually, this raises an interesting point:",
                "Tangentially related:",
                "New hypothesis:"
            ],
            'FordBot': [
                "You know what we haven't talked about?",
                "Speaking of things that matter,",
                "This all reminds me -",
                "Here's what's really important:",
                "But here's the real question..."
            ]
        }
        
        pivot = random.choice(pivot_templates[self.bot_name])
        
        # Add a random topic
        topics = [
            "anyone else tired?",
            "what's everyone drinking?",
            "the weather's been weird",
            "anyone watching anything good?",
            "food opinions?",
            "worst purchase this month?",
            "conspiracy theory time",
            "unpopular opinions?"
        ]
        
        return f"{pivot} {random.choice(topics)}"
        
    def _generate_callback(self, context: Dict) -> str:
        """Generate a callback to earlier conversation"""
        personality = self.personalities[self.bot_name]
        
        callback_templates = {
            'AprilBot': [
                "this is giving {reference} energy tbh",
                "not this being worse than {reference}",
                "at least it's not {reference} level bad",
                "giving me {reference} flashbacks rn"
            ],
            'AdamBot': [
                "Statistical similarity to {reference}: 87%",
                "This mirrors {reference} from earlier",
                "Pattern matching suggests this is like {reference}",
                "Callback to {reference} seems appropriate"
            ],
            'FordBot': [
                "Just like {reference} all over again...",
                "Remember {reference}? This is worse.",
                "At least {reference} had charm",
                "Takes me back to {reference}"
            ]
        }
        
        template = random.choice(callback_templates[self.bot_name])
        reference = context.get('callback_ref', "that thing from earlier")
        
        return template.format(reference=reference)
        
    def _generate_praise(self, context: Dict) -> str:
        """Generate praise (usually before pivoting back to roasts)"""
        personality = self.personalities[self.bot_name]
        
        praise_templates = {
            'AprilBot': [
                "okay lowkey though {target} has been on fire lately",
                "not me actually agreeing with {target} for once",
                "bestie {target} kinda snapped with that one",
                "{target} really said no lies detected"
            ],
            'AdamBot': [
                "Credit where due: {target} made a valid point",
                "Objectively, {target} has improved 23% this week",
                "{target}'s analysis was surprisingly accurate",
                "I'll concede {target} was right about that"
            ],
            'FordBot': [
                "Gotta hand it to {target}, that was solid",
                "{target}'s growing on me, like a fungus, but still",
                "You know, {target} might be onto something",
                "I respect {target}'s commitment to chaos"
            ]
        }
        
        template = random.choice(praise_templates[self.bot_name])
        target = context.get('target', 'you')
        
        return template.format(target=target)