# AI Roast Den - Architecture (Sprint 0)

## Overview
This document describes the new Fargate-based architecture that solves the Lambda 15-minute timeout issue.

## Architecture Diagram
```
Discord WebSocket → Fargate Container (24/7)
                          ↓
                    SQS Message Queue
                          ↓
                 Lambda Functions (Per Message)
                          ↓
                    DynamoDB | Bedrock
```

## Components

### 1. Fargate Container (bot_container.py)
- **Purpose**: Maintains persistent Discord WebSocket connection
- **Features**:
  - 24/7 uptime with auto-restart on failure
  - Health check endpoint on port 8080
  - Sends messages to SQS for async processing
  - Lightweight - only handles Discord events
- **Resources**: 0.5 GB RAM, 0.25 vCPU
- **Cost**: ~$10/month

### 2. SQS Queue
- **Purpose**: Decouples Discord events from AI processing
- **Features**:
  - Message retention: 1 day
  - Dead letter queue for failed messages
  - Visibility timeout: 5 minutes
- **Cost**: ~$0.40/million messages

### 3. Lambda Message Processor
- **Purpose**: Process AI requests without blocking Discord
- **Features**:
  - Calls Claude AI via Bedrock
  - Manages conversation memory
  - Can scale to handle bursts
  - 5-minute timeout (plenty for AI)
- **Cost**: ~$0.20/1000 requests

### 4. DynamoDB Memory Table
- **Purpose**: Store conversation history
- **Schema**:
  - Partition Key: bot_name
  - Sort Key: timestamp
  - TTL: 30 days for short-term memory
- **Cost**: ~$5/month with on-demand

## Deployment Instructions

### Prerequisites
1. AWS CLI configured with appropriate credentials
2. AWS CDK installed (`npm install -g aws-cdk`)
3. Docker installed for building container images
4. Python 3.11+ installed

### First-Time Setup
```bash
# Bootstrap CDK (only needed once per account/region)
cdk bootstrap

# Create Discord token secret in AWS Secrets Manager
aws secretsmanager create-secret \
    --name simulchaos/discord \
    --secret-string '{"DISCORD_TOKEN":"your-bot-token-here"}'
```

### Deploy Infrastructure
```bash
# Install dependencies
pip install -r requirements.txt

# Deploy the stack
cdk deploy

# Watch the logs
aws logs tail /ecs/simulchaos-bot --follow
```

### Update Bot Code
```bash
# After making changes to bot_container.py
cdk deploy

# The new container will be deployed with zero downtime
```

## Monitoring

### CloudWatch Dashboard
The stack creates a dashboard named "SimulchaosBot" with:
- Container health metrics (CPU, Memory)
- Message queue depth
- Lambda invocations and errors
- Claude AI performance metrics

### Key Metrics to Watch
- `BotHeartbeat`: Should tick every 30 seconds
- `SQSMessageSent`: Messages sent to queue
- `MessageProcessed`: Successfully processed messages
- `ClaudeResponseTime`: AI response latency

## Cost Breakdown (Estimated Monthly)
- Fargate Container: $10
- Lambda Invocations: $5 (at 100k messages)
- SQS: $1
- DynamoDB: $5
- CloudWatch: $2
- **Total: ~$23/month**

## Next Steps (Sprint 1)
1. Create personality system with JSON files
2. Remove hardcoded "FordBot" references
3. Implement proper Discord message updates
4. Add rate limiting
5. Create admin commands

## Troubleshooting

### Bot Not Responding
1. Check ECS service in AWS Console
2. View container logs: `aws logs tail /ecs/simulchaos-bot`
3. Verify Discord token is correct in Secrets Manager

### Messages Not Processing
1. Check SQS queue depth in CloudWatch
2. View Lambda logs for errors
3. Check Dead Letter Queue for failed messages

### High Costs
1. Review CloudWatch dashboard for usage spikes
2. Check Lambda invocation count
3. Ensure DynamoDB TTL is working