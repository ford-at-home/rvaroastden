# Discord Bot Conversation Status - July 7, 2025

## Current State
- **All 3 bot services deleted**: AprilBot, AdamBot, FordBot services removed from ECS
- **CloudFormation stacks deleted**: Individual bot stacks removed
- **Infrastructure preserved**: 
  - ECS cluster (discord-bot-cluster) - empty, $0/day
  - All Discord secrets in AWS Secrets Manager
  - ECR repository with container images
  - CodeBuild project (firepit-discord-bot-build)
  - BotInfraStack still active

## Latest Code Status

### Commits Made (in order):
1. Fix missing template variable in story generation
2. Reduce bot noise: double thresholds and add 8pm-8am EST quiet hours
3. Add topic coherence rules - min 3 exchanges before pivot
4. Add error handling with fallback to reply generator
5. Emergency fix: bypass story generation for AprilBot
6. Reduce bot chattiness by 50% more: rate limit 10msg/hr, lower probabilities, longer silence thresholds

### Current Bot Configuration:
- **Scan interval**: 10 seconds (was 5)
- **Dead air threshold**: 15 seconds (was 4)
- **Dead air override**: 2 minutes (was 30 seconds)
- **User deference**: 6 turns (was 3)
- **Speaking probability**: Halved twice from original
  - FordBot: 3.75% base
  - AprilBot: 2.5% base
  - AdamBot: 3% base
- **Rate limiting**: 10 messages/hour max, then 1-hour backoff
- **Quiet hours**: 8pm-8am EST
- **Topic coherence**: Minimum 3 exchanges before allowing topic change

### Known Issues:
1. **AprilBot story generation bug**: Template placeholders don't match format() keys
   - Temporary fix: Bypass story generation, return riff instead
   - Permanent fix needed: Align template placeholders with format keys

2. **CloudWatch permissions**: All bots lack PutMetricData permission
   - Non-critical, just creates log noise

3. **Docker build failures**: Rate limits causing intermittent CodeBuild failures
   - Workaround: Retry builds until successful

## Last Successful Build
- Build ID: firepit-discord-bot-build:6e442c88-0e93-458a-9ce1-da789af0832f
- Contains: Emergency fix for AprilBot story generation
- Does NOT contain: Latest rate limiting (10 msg/hr)

## To Resume:

### Quick Restart (with current fixes):
```bash
# Deploy all three bots with existing fixes
cdk deploy AprilBotStack AdamBotStack FordBotStack --require-approval never
```

### Full Fix Implementation:
1. Fix AprilBot story template properly:
   - Align all template placeholders with format() parameters
   - Test all reply types

2. Add CloudWatch permissions to task roles:
   - Add cloudwatch:PutMetricData to each bot's task role

3. Deploy with latest changes:
   - Ensure latest commits are built and deployed
   - Verify rate limiting is working

### Cost When Running:
- 3 bots × $0.29/day = $0.87/day
- Plus ~$0.05/day for secrets and logs
- Total: ~$0.92/day when active

### Branch Status:
- Working on: main branch
- Feature branch: feature/firepit-discord-update (merged)

## Key Decisions Made:
1. Reduced bot noise by ~75% total from original
2. Added quiet hours for overnight silence
3. Implemented topic coherence to prevent random pivots
4. Added rate limiting to prevent spam
5. Decided to shut down bots until fixes are properly deployed

## Next Steps When Resuming:
1. Fix AprilBot's story generation properly
2. Add CloudWatch permissions
3. Test locally if possible
4. Deploy with all fixes
5. Monitor for appropriate chat frequency
6. Fine-tune thresholds based on actual usage