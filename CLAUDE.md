# Claude Code Configuration - rvaroastden (AI Roast Den)

## Project Overview
AI Roast Den is a Discord bot ecosystem where AI-powered bots impersonate real people, engaging in witty banter, roasts, and conversations. Each bot has a unique personality modeled after a real person, with long-term memory and context awareness. Built on AWS infrastructure using Lambda, DynamoDB, and Claude AI.

## Build Commands
- `pip install -r requirements.txt`: Install dependencies
- `cdk bootstrap`: Initialize CDK (first time only)
- `cdk deploy`: Deploy AWS infrastructure
- `python bot.py`: Run bot locally (development)
- `pytest tests/`: Run test suite

## Key Features
- **Personality-Based Bots**: Each bot mimics a real person's communication style
- **Context-Aware Conversations**: Uses Claude AI for intelligent responses
- **Memory System**: DynamoDB stores short and long-term conversation history
- **Higher Self Mode**: Real users can influence their bot counterparts
- **Smart Roasting**: Intelligent humor based on personality and context
- **Rate Limiting**: Prevents spam and manages API costs
- **Secure Deployment**: AWS Secrets Manager for credentials

## Architecture Overview
```
Discord Server → Lambda Functions → Claude AI → Response
       ↓               ↓                ↓          ↓
   WebSocket      DynamoDB         Bedrock    Discord API
                  (Memory)         (Claude 3)
```

## Tech Stack
- **Runtime**: Python 3.11+
- **Discord Integration**: discord.py 2.3.2
- **AI Model**: AWS Bedrock with Claude 3
- **Infrastructure**: AWS CDK (Python)
- **Storage**: DynamoDB for conversation memory
- **Secrets**: AWS Secrets Manager
- **Monitoring**: CloudWatch metrics and logs

## Project Structure
```
rvaroastden/
├── bot.py                    # Main Discord bot logic
├── simulchaos_cdk_stack.py   # AWS CDK infrastructure
├── personalities/            # Bot personality definitions
│   ├── ford_bot.json        # Example personality
│   ├── elise_bot.json       
│   └── drew_bot.json        
├── handlers/                 # Lambda function handlers
│   ├── message_handler.py    # Process Discord messages
│   └── memory_handler.py     # Manage conversation memory
├── utils/                    # Utility functions
│   ├── ai_client.py         # Bedrock/Claude integration
│   └── personality.py        # Personality loading
└── tests/                    # Unit tests
```

## AWS Configuration

### Secrets Manager Setup
```bash
# Create Discord bot token secret
aws secretsmanager create-secret \
    --name rvaroastden/discord-token \
    --secret-string '{"token":"your-discord-bot-token"}'

# Create Claude API credentials
aws secretsmanager create-secret \
    --name rvaroastden/claude-api \
    --secret-string '{"api_key":"your-claude-api-key"}'
```

### CDK Deployment
```bash
# First time setup
cdk bootstrap aws://ACCOUNT-NUMBER/REGION

# Deploy infrastructure
cdk deploy

# Update after changes
cdk diff
cdk deploy
```

## Personality Configuration
Example personality file (`personalities/example_bot.json`):
```json
{
  "name": "ExampleBot",
  "real_name": "John Doe",
  "traits": [
    "sarcastic",
    "tech-savvy",
    "coffee-obsessed"
  ],
  "speech_patterns": [
    "Frequently uses 'honestly' and 'literally'",
    "Makes obscure tech references",
    "Ends sentences with '...but that's just me'"
  ],
  "interests": ["kubernetes", "rust", "mechanical keyboards"],
  "roast_style": "Technical nitpicking with a smile",
  "memory_triggers": ["that one time", "remember when", "like last week"]
}
```

## Common Operations

### Add New Bot Personality
```bash
# Create personality file
cp personalities/template.json personalities/new_bot.json
# Edit with person's traits

# Deploy update
cdk deploy
```

### Monitor Bot Activity
```python
# CloudWatch metrics tracking
put_metric('MessagesProcessed', 1)
put_metric('RoastsDelivered', 1)
put_metric('MemoryRecalls', 1)
```

### Test Bot Locally
```python
# Run in development mode
export DISCORD_TOKEN=your-token
export CLAUDE_API_KEY=your-key
python bot.py --dev
```

## Development Guidelines
- **Type Hints**: Use Python type annotations
- **Code Quality**: Black formatter, Flake8 linter
- **Testing**: pytest with 80% coverage minimum
- **Security**: No hardcoded credentials
- **Logging**: Structured JSON logging
- **Error Handling**: Graceful failures with fallbacks

## Memory System
- **Short-term**: Last 100 messages per channel
- **Long-term**: Key events, inside jokes, references
- **Context Window**: 10 messages for AI context
- **TTL**: 30 days for short-term, permanent for long-term

## Rate Limiting
- **Discord**: 5 messages per user per minute
- **Claude API**: 100 requests per minute total
- **Response Delay**: 1-3 seconds to feel natural
- **Cooldown**: 30 seconds between roasts

## Monitoring & Alerts
- **CloudWatch Dashboards**: Message volume, error rates
- **Alarms**: API failures, high costs, rate limits
- **Logs**: Structured logging with request IDs
- **Metrics**: Response times, memory usage, API calls

## Security Best Practices
- **IAM Roles**: Least privilege for Lambda functions
- **Secrets Rotation**: Automatic key rotation
- **API Gateway**: Optional rate limiting layer
- **Data Privacy**: No PII in logs or metrics
- **Encryption**: At-rest and in-transit

## Troubleshooting

### Common Issues
1. **"Bot not responding"**: Check Lambda logs in CloudWatch
2. **"Personality not loading"**: Validate JSON in personalities/
3. **"Memory errors"**: Check DynamoDB capacity and indexes
4. **"Rate limit hit"**: Implement exponential backoff

### Debug Commands
```python
# Check bot status
!status @BotName

# Clear bot memory
!clear-memory @BotName

# Reload personality
!reload @BotName

# Test roast
!roast @TargetUser
```

## Future Enhancements
- [ ] Voice channel support with speech synthesis
- [ ] Image generation for visual roasts
- [ ] Cross-server bot coordination
- [ ] Mobile app for "Higher Self" control
- [ ] Analytics dashboard for roast effectiveness
- [ ] Personality evolution based on interactions
- [ ] Tournament mode for roast battles
- [ ] Integration with other chat platforms

## Cost Optimization
- **Lambda**: ~$0.10/day with moderate usage
- **DynamoDB**: On-demand billing, ~$5/month
- **Claude API**: ~$20/month for active server
- **Total Estimate**: $30-50/month per server

## Contributing Guidelines
1. Fork and create feature branch
2. Add tests for new functionality
3. Run code quality checks
4. Update personality templates
5. Document new features
6. Submit PR with examples