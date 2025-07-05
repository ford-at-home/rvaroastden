#!/bin/bash
# AI Roast Den - Final Deployment Script with Virtual Environment

set -e

echo "🚀 AI Roast Den - Final Deployment"
echo "=================================="

# Set AWS profile and region
export AWS_PROFILE=personal
export AWS_DEFAULT_REGION=us-east-1
echo "✓ Using AWS profile: personal"
echo "✓ Using AWS region: us-east-1"

# Check prerequisites
echo ""
echo "📋 Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed."
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed."
    exit 1
fi

if ! command -v cdk &> /dev/null; then
    echo "❌ AWS CDK is not installed. Run: npm install -g aws-cdk"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    exit 1
fi

echo "✓ All prerequisites met!"

# Check Discord secret
echo ""
echo "🔐 Checking Discord secret..."
if aws secretsmanager describe-secret --secret-id simulchaos/discord &> /dev/null; then
    echo "✓ Discord token secret exists"
else
    echo "❌ Discord token secret not found!"
    exit 1
fi

# Create and activate virtual environment
echo ""
echo "🐍 Setting up Python environment..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check CDK bootstrap
echo ""
echo "🔧 Checking CDK Bootstrap..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "Running CDK bootstrap..."
    cdk bootstrap aws://$ACCOUNT_ID/us-east-1
else
    echo "✓ CDK already bootstrapped"
fi

# Deploy
echo ""
echo "🚀 Deploying CDK Stack..."
echo "This will take 5-10 minutes..."
echo ""

cdk deploy --require-approval never

# Get outputs
echo ""
echo "✅ Deployment Complete!"
echo "===================="

# Get stack outputs
CLUSTER_NAME=$(aws cloudformation describe-stacks \
    --stack-name SimulchaosStack \
    --query "Stacks[0].Outputs[?OutputKey=='ClusterName'].OutputValue" \
    --output text 2>/dev/null || echo "N/A")

SERVICE_NAME=$(aws cloudformation describe-stacks \
    --stack-name SimulchaosStack \
    --query "Stacks[0].Outputs[?OutputKey=='ServiceName'].OutputValue" \
    --output text 2>/dev/null || echo "N/A")

echo "Cluster: $CLUSTER_NAME"
echo "Service: $SERVICE_NAME"

echo ""
echo "📱 Discord Commands:"
echo "=================="
echo "!help                    - Show all commands"
echo "!ask <question>          - Get roasted by a random bot"
echo "!summon ford <question>  - Summon Ford's consciousness debugging"
echo "!summon april <question> - Summon April's chaos energy"
echo "!summon adam <question>  - Summon Adam's system analysis"
echo "!status                  - Check bot status"

echo ""
echo "📊 Monitor Your Bots:"
echo "==================="
echo "aws logs tail /ecs/simulchaos-bot --follow --profile personal"

echo ""
echo "🔥 The AI Roast Den is LIVE! Check Discord for your bots!"

# Deactivate virtual environment
deactivate