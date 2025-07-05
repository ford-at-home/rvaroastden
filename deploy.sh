#!/bin/bash
# AI Roast Den - Deployment Script

set -e

echo "🚀 AI Roast Den - Sprint 0 Deployment"
echo "======================================"

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

# Set AWS profile and region
export AWS_PROFILE=personal
export AWS_DEFAULT_REGION=us-east-1
echo "✓ Using AWS profile: personal"
echo "✓ Using AWS region: us-east-1"

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured for profile 'personal'. Run: aws configure --profile personal"
    exit 1
fi

echo "✓ All prerequisites met!"

# Get Discord token
echo ""
echo "📝 Discord Bot Setup"
echo "==================="
echo "Have you created the Discord bot token secret? (y/n)"
read -r response

if [[ "$response" != "y" ]]; then
    echo ""
    echo "Please create the secret first:"
    echo "aws secretsmanager create-secret \\"
    echo "    --name simulchaos/discord \\"
    echo "    --secret-string '{\"DISCORD_TOKEN\":\"your-bot-token-here\"}'"
    exit 1
fi

# CDK Bootstrap (if needed)
echo ""
echo "🔧 Checking CDK Bootstrap..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)

if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "Running CDK bootstrap..."
    cdk bootstrap aws://$ACCOUNT_ID/$REGION
else
    echo "✓ CDK already bootstrapped"
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Deploy stack
echo ""
echo "🚀 Deploying CDK Stack..."
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
echo "   aws logs tail /ecs/simulchaos-bot --follow"
echo ""
echo "2. Check service status:"
echo "   aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME"
echo ""
echo "3. View CloudWatch dashboard:"
echo "   https://console.aws.amazon.com/cloudwatch/home?region=$REGION#dashboards:name=SimulchaosBot"
echo ""
echo "4. Test the bot in Discord with: !ask <question>"

echo ""
echo "✅ Deployment complete! The bot should be online in Discord within 2 minutes."