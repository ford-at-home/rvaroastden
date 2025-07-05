# 🔥 AI Roast Den: Multi-Bot Discord Ecosystem with Autonomous Conversations

Welcome to the AI Roast Den — a Discord playground where AI versions of you and your friends roast, riff, and reflect in ongoing group chats. Each bot has a detailed personality, memory system, and **autonomous conversation intelligence** that decides when and how to naturally participate in discussions.

## 🎭 The Personality Bots

### 🧘‍♂️ **FordBot** - The Contemplative Strategist
- **Style**: Drops philosophical wisdom bombs then goes mysteriously silent
- **Triggers**: Deep questions, meaning-of-life discussions, tech philosophy
- **Reply Pattern**: Waits for profound moments, makes observations, then retreats
- **Commands**: `!ford roast`, `@FordBot ask`, `!ford status`

### 🎪 **AprilBot** - The Chaotic Interruptor  
- **Style**: Cannot resist disrupting boring conversations with theatrical chaos
- **Triggers**: Orderly discussions, Ford being too philosophical, low energy
- **Reply Pattern**: Feeds off others' energy, creates conversational mayhem
- **Commands**: `!april roast`, `@AprilBot ask`, `!april status`

### 🥁 **AdamBot** - The Rhythmic Opportunist
- **Style**: Waits for perfect timing to drop beats and burns
- **Triggers**: Music references, punchline setups, rhythm disruptions  
- **Reply Pattern**: Establishes conversation flow, strikes with perfect timing
- **Commands**: `!adam roast`, `@AdamBot ask`, `!adam status`

## 🧠 Autonomous Conversation System (V2)

The bots don't just respond to commands — they **autonomously decide** when to join conversations using sophisticated AI-powered decision making.

### 🚫 **Hard Rules** (Non-Negotiable):
1. **No Double Replies**: Bots can't reply to themselves consecutively
2. **Wait for Response**: If FordBot addresses AdamBot, Ford must wait for Adam/April to reply first
3. **Cooldown Period**: 30-second minimum between replies
4. **Rate Limiting**: Maximum 20 replies per hour per bot

### 🎭 **Vibe Rules** (Personality-Based Probability):

| Bot | Base Chance | Personality Triggers | Conversation Style |
|-----|-------------|---------------------|-------------------|
| **FordBot** | 30% | Philosophy (+70%), Being Roasted (+80%), Tech Deep-Dives (+60%) | Contemplative pauses, wisdom drops |
| **AprilBot** | 60% | Chaos Needed (+80%), Boring Conversations (+90%), Ford Being Philosophical (+90%) | High-energy disruption, theatrical flair |
| **AdamBot** | 40% | Music Topics (+80%), Perfect Timing (+90%), Punchline Setups (+95%) | Rhythmic flow, perfectly-timed burns |

### 🤖 **Claude-Powered Decision Engine**:
When reply probability > 30%, the system asks Claude to evaluate:
- Is this good timing for this specific bot?
- Would their response add value or humor?
- Does the conversation need their particular energy?

Claude can adjust the final probability by up to 30%, ensuring natural conversation flow.

### 💬 **Interaction Dynamics**:
- **Ford ↔ April**: Wisdom vs. Chaos (April gets +20% boost to disrupt Ford's philosophy)
- **April ↔ Adam**: Chaos vs. Rhythm (Creates comedy gold, +15% back-and-forth boost)  
- **Adam ↔ Ford**: Beats vs. Meditation (Mutual respect, philosophical music discussions)

### 🎯 **Special Triggers**:
- **"roast battle"** → All bots become 30% more active for 5 minutes
- **Philosophy keywords** → Ford +40%, April +60% disruption chance
- **Music references** → Adam +50% activation
- **Chaos words** ("wild", "crazy", "circus") → April +40% activation

## 🏗️ Architecture

### **Multi-Bot Infrastructure**:
- **3 separate ECS tasks** - Each bot runs independently with its own Discord token
- **Shared Lambda** - Single AI processing engine for all personalities
- **DynamoDB Memory** - Cross-bot conversation history and personality memories
- **SQS Queue** - Async message processing for scalability

### **AWS Stack**:
- **Discord Bots**: AWS Fargate containers (persistent connections)
- **AI Processing**: AWS Lambda + Bedrock (Claude 3)
- **Memory**: DynamoDB with TTL for conversation history
- **Secrets**: AWS Secrets Manager for Discord tokens
- **Infrastructure**: AWS CDK for deployment

## 🚀 Deployment

### **Prerequisites**:
- Python 3.11+
- AWS CLI configured
- AWS CDK CLI (`brew install aws-cdk`)
- Node.js
- Discord Developer Applications for each bot

### **Quick Setup**:

1. **Clone and Install**:
   ```bash
   git clone <repo>
   cd rvaroastden
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Store Discord Tokens**:
   ```bash
   # For each bot, store token in AWS Secrets Manager
   aws secretsmanager create-secret \
       --name simulchaos/discord-ford \
       --secret-string '{"DISCORD_TOKEN":"YOUR_FORD_BOT_TOKEN"}'
   
   aws secretsmanager create-secret \
       --name simulchaos/discord-april \
       --secret-string '{"DISCORD_TOKEN":"YOUR_APRIL_BOT_TOKEN"}'
   
   aws secretsmanager create-secret \
       --name simulchaos/discord-adam \
       --secret-string '{"DISCORD_TOKEN":"YOUR_ADAM_BOT_TOKEN"}'
   ```

3. **Deploy Infrastructure**:
   ```bash
   ./deploy_multibot.sh
   # Or manually: cdk deploy SimulchaosMultiBotStack --profile personal
   ```

4. **Invite Bots to Discord**:
   Use OAuth URLs with permissions integer `277025778752`:
   ```
   https://discord.com/api/oauth2/authorize?client_id=YOUR_BOT_ID&permissions=277025778752&scope=bot
   ```

## 🎮 Usage Examples

### **Command-Based Interactions**:
```
User: !ford roast Mike's coding skills
FordBot: 🧘‍♂️ *FordBot is contemplating...*
FordBot: Mike's code is like his meditation practice - lots of sitting, little enlightenment.

User: @AprilBot what do you think about serverless?
AprilBot: 🎪 *AprilBot is channeling their energy...*
AprilBot: Serverless? More like CLUELESS! *juggling cloud instances* Next you'll tell me containers are just fancy boxes!
```

### **Autonomous Conversations**:
```
User1: I'm really struggling with this React component
FordBot: The path to enlightenment often involves accepting that useState is not the way
User2: Lol Ford getting philosophical about hooks
AprilBot: 🎪 *spins plates menacingly*
AprilBot: BEHOLD! The great Ford has spoken! *dramatic bow* Perhaps we should consult the ancient texts of Stack Overflow!
AdamBot: 🥁 *taps fingers rhythmically*  
AdamBot: Y'all are debating React like it's the meaning of life. Maybe try turning it off and on again? *drops sick beat*
```

## 🎯 Conversation Flow Examples

**Scenario 1 - Ford addresses Adam directly**:
```
FordBot: @AdamBot what's your take on algorithmic composition?
❌ FordBot: (Cannot reply again until Adam or April responds)
✅ AdamBot: *drops philosophical beat* When the algorithm finds the groove, man...
✅ FordBot: (Now can reply again)
```

**Scenario 2 - April's chaos injection**:
```
User1: The quarterly reports show steady growth
User2: Yes, our metrics are quite promising
AprilBot: (90% chance to disrupt boring conversation)
AprilBot: 🎪 METRICS?! *throws confetti* Let me introduce you to the metric that matters - CHAOS PER SECOND!
```

**Scenario 3 - Adam's perfect timing**:
```
User: I tried to write a song but...
AprilBot: But WHAT? The suspense is killing me!
AdamBot: (95% chance for punchline setup)
AdamBot: 🥁 ...but it was more like noise pollution? *rim shot* Been there, my friend.
```

## 🔧 Customization

### **Adding New Personalities**:
1. Create `/personalities/newbot.json` with traits, speech patterns, and roast style
2. Add bot configuration to CDK stack
3. Update conversation rules with new bot's vibe rules
4. Deploy updated infrastructure

### **Tuning Conversation Behavior**:
- Edit `/conversation_rules.json` to adjust reply probabilities
- Modify personality modifiers for different triggers
- Add new special triggers and interaction dynamics
- Update hard rules for different conversation flows

### **Memory System**:
- Bots remember both command responses and autonomous conversations
- Long-term memory for inside jokes and references
- Context-aware responses based on conversation history
- Cross-bot memory sharing for group dynamics

## 📊 Monitoring

**CloudWatch Metrics**:
- Per-bot message counts and response times
- Autonomous reply rates and decision reasons
- Claude API usage and success rates
- Memory system operations

**ECS Health Checks**:
- Bot connectivity status
- Resource utilization per personality
- Auto-scaling based on conversation activity

## 🎭 Personality Development

Each bot's personality is defined by:

- **Core Traits**: Fundamental characteristics (sarcastic, philosophical, chaotic)
- **Speech Patterns**: How they communicate (metaphors, catchphrases, style)
- **Interests**: Topics that trigger higher engagement
- **Roast Style**: Their approach to humor and burns
- **Conversation Style**: How they participate in group dynamics
- **Memory Triggers**: What they remember and reference

## 🚀 Future Enhancements

- **Voice Channel Support**: Speech synthesis for audio roasts
- **Cross-Server Coordination**: Bots working across multiple Discord servers  
- **Higher Self Mode**: Real users influencing their bot counterparts
- **Tournament Mode**: Structured roast battles with scoring
- **Analytics Dashboard**: Conversation analysis and bot effectiveness metrics
- **Personality Evolution**: Bots adapting based on interactions over time

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Update personality templates and documentation
5. Submit PR with examples of new behavior

## 📜 License

MIT License - Build your own AI roast army!

---

*"In a world where humans and AI coexist, someone had to teach the machines how to roast properly."* - The AI Roast Den Philosophy