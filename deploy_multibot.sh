#!/bin/bash
# Deploy multi-bot infrastructure

echo "🤖 Deploying AI Roast Den Multi-Bot System..."

# Check if we're transitioning from single bot to multi-bot
if aws ecs describe-services --cluster simulchaos-bot-cluster --services simulchaos-bot-service --profile personal --region us-east-1 &>/dev/null; then
    echo "⚠️  Found existing single-bot deployment. Stopping it first..."
    aws ecs update-service --cluster simulchaos-bot-cluster --service simulchaos-bot-service --desired-count 0 --profile personal --region us-east-1
    echo "Waiting for existing bot to stop..."
    sleep 30
fi

# Deploy the new multi-bot stack
echo "📦 Deploying multi-bot CDK stack..."
cd /Users/williamprior/Development/GitHub/rvaroastden
source venv/bin/activate
cdk deploy SimulchaosMultiBotStack --profile personal --require-approval never

echo "✅ Multi-bot deployment complete!"
echo ""
echo "📊 Bot Status:"
echo "- FordBot: 🧘‍♂️ simulchaos-fordbot-service" 
echo "- AprilBot: 🎪 simulchaos-aprilbot-service"
echo "- AdamBot: 🥁 simulchaos-adambot-service"
echo ""
echo "Use these commands to check bot status:"
echo "aws ecs list-tasks --cluster simulchaos-multibot-cluster --profile personal --region us-east-1"