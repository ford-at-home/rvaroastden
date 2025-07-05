#!/bin/bash
# AI Roast Den - Automated Deployment Script

set -e

echo "🚀 AI Roast Den - Automated Deployment"
echo "======================================"

# Set AWS profile and region
export AWS_PROFILE=personal
export AWS_DEFAULT_REGION=us-east-1
echo "✓ Using AWS profile: personal"
echo "✓ Using AWS region: us-east-1"

# Check prerequisites
echo "✓ Checking prerequisites..."

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK is not installed. Run: npm install -g aws-cdk"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker Desktop."
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured for profile 'personal'."
    exit 1
fi

echo "✓ All prerequisites met!"

# Check if Discord token secret exists
echo ""
echo "📝 Checking Discord Bot Secret..."
if aws secretsmanager describe-secret --secret-id simulchaos/discord &> /dev/null; then
    echo "✓ Discord token secret already exists"
else
    echo "❌ Discord token secret not found!"
    echo ""
    echo "Please create it with:"
    echo "aws secretsmanager create-secret \\"
    echo "    --name simulchaos/discord \\"
    echo "    --secret-string '{\"DISCORD_TOKEN\":\"your-bot-token-here\"}' \\"
    echo "    --profile personal --region us-east-1"
    exit 1
fi

# CDK Bootstrap (if needed)
echo ""
echo "🔧 Checking CDK Bootstrap..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "Running CDK bootstrap..."
    cdk bootstrap aws://$ACCOUNT_ID/us-east-1 --profile personal
else
    echo "✓ CDK already bootstrapped"
fi

# Install dependencies
echo ""
echo "📦 Checking Python dependencies..."
echo "   Note: CDK is already installed globally via npm"
echo "   Python dependencies are for local development only"

# Deploy stack
echo ""
echo "🚀 Deploying CDK Stack..."
echo "This will take about 5-10 minutes..."
cdk deploy --require-approval never --profile personal

# Get outputs
echo ""
echo "📊 Deployment Complete!"
echo "======================"

# Get stack outputs
CLUSTER_NAME=$(aws cloudformation describe-stacks \
    --stack-name SimulchaosStack \
    --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
    --output text)

SERVICE_NAME=$(aws cloudformation describe-stacks \
    --stack-name SimulchaosStack \
    --query "Stacks[0].Outputs[?OutputKey=='ServiceName'].OutputValue" \
    --output text)

QUEUE_URL=$(aws cloudformation describe-stacks \
    --stack-name SimulchaosStack \
    --query "Stacks[0].Outputs[?OutputKey=='QueueUrl'].OutputValue" \
    --output text)

echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"
echo "Queue: $QUEUE_URL"

echo ""
echo "📋 Next Steps:"
echo "============="
echo "1. View container logs:"
echo "   aws logs tail /ecs/simulchaos-bot --follow --profile personal"
echo ""
echo "2. Check service status:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --profile personal"
echo ""
echo "3. View CloudWatch dashboard:"
echo "   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=SimulchaosBot"
echo ""
echo "4. Test the bot in Discord with:"
echo "   !help"
echo "   !ask What do you think of my code?"
echo "   !summon ford Tell me about serverless"
echo "   !summon april What's your startup advice?"
echo "   !summon adam Analyze my team dynamics"

echo ""
echo "✅ Deployment complete! The bot should be online in Discord within 2 minutes."
echo ""
echo "🔥 Let the roasting begin!"