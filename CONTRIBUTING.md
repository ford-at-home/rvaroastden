# Contributing Guide

## Prerequisites

Before you begin, ensure you have the following installed:

1. **Python 3.11+**
   ```bash
   python3 --version  # Should be 3.11 or higher
   ```

2. **AWS CLI**
   ```bash
   brew install awscli
   aws configure  # Set up your AWS credentials
   ```

3. **AWS CDK CLI**
   ```bash
   brew install aws-cdk
   cdk --version  # Verify installation
   ```

4. **Node.js** (required for CDK)
   ```bash
   brew install node
   node --version  # Verify installation
   ```

5. **Git**
   ```bash
   brew install git
   git --version  # Verify installation
   ```

## Development Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/ford-at-home/rvaroastden.git
   cd rvaroastden
   ```

2. **Set Up Virtual Environment**
   ```bash
   make venv
   make install
   ```

## Development Workflow

1. **Create a New Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Run code quality checks:
     ```bash
     pytest tests/
     ```

3. **Test Your Changes**
   ```bash
   make test
   ```

4. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

5. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Deployment

### Local Deployment

1. **Bootstrap CDK** (first time only)
   ```bash
   make bootstrap
   ```

2. **Deploy Stack**
   ```bash
   make deploy
   ```

3. **Destroy Stack** (if needed)
   ```bash
   make destroy
   ```

### CI/CD Deployment

The project uses GitHub Actions for automated deployment. The workflow:

1. **Triggers on**:
   - Push to main branch
   - Pull requests to main branch

2. **Test Job**:
   - Runs code quality checks
   - Executes tests
   - Must pass before deployment

3. **Deploy Job**:
   - Only runs on push to main
   - Requires test job success
   - Deploys CDK stack

### Required GitHub Secrets

Set these in your repository settings:

- `AWS_ROLE_ARN`: IAM role ARN for GitHub Actions
- `AWS_ACCOUNT_ID`: Your AWS account ID

### IAM Role Setup

1. **Create OIDC Provider**
   ```bash
   aws iam create-open-id-connect-provider \
       --url https://token.actions.githubusercontent.com \
       --client-id-list sts.amazonaws.com \
       --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
   ```

2. **Create IAM Role**
   - Trust policy:
     ```json
     {
         "Version": "2012-10-17",
         "Statement": [
             {
                 "Effect": "Allow",
                 "Principal": {
                     "Federated": "arn:aws:iam::<YOUR-ACCOUNT-ID>:oidc-provider/token.actions.githubusercontent.com"
                 },
                 "Action": "sts:AssumeRoleWithWebIdentity",
                 "Condition": {
                     "StringEquals": {
                         "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                     },
                     "StringLike": {
                         "token.actions.githubusercontent.com:sub": "repo:<YOUR-GITHUB-USERNAME>/<YOUR-REPO-NAME>:*"
                     }
                 }
             }
         ]
     }
     ```
   - Required permissions:
     - CloudFormation full access
     - IAM full access
     - Lambda full access
     - Secrets Manager full access
     - DynamoDB full access
     - CloudWatch full access

## Code Quality

### Pre-commit Hooks

Automatically run on commit:
- Black formatting
- Flake8 linting
- Type checking

### Manual Checks

Run these before pushing:
```bash
make format  # Format code
make lint    # Lint code
make type-check  # Type check
make test    # Run tests
```

Or run all checks:
```bash
make dev
```

## Troubleshooting

### Common Issues

1. **Pre-commit Hooks Fail**
   - Run `make format` to fix formatting
   - Run `make lint` to fix linting issues

2. **Deployment Fails**
   - Check AWS credentials
   - Verify IAM permissions
   - Check CloudWatch logs

3. **Tests Fail**
   - Run tests locally: `make test`
   - Check test logs for details

### Getting Help

- Check CloudWatch logs
- Review GitHub Actions logs
- Open an issue with detailed information

# Contributing Your Personality to the AI Roast Den

Want to see your digital twin in the chatroom? Amazing. Here's how to bring your unhinged AI self to life.

---

## Step 1: Fork the Repo

Fork this repository and create a branch for your agent, e.g. `add/my-bot`.

---

## Step 2: Create Your Personality File

Add a YAML file in the `personalities/` directory named after your bot:

```bash
personalities/
└── drew.yaml
```

### Template

```yaml
name: DrewBot
avatar_url: https://example.com/avatar.png
speaking_style: dry, sarcastic, extremely online
expertise:
  - distributed systems
  - Rust
  - anime logic
curiosity_zones:
  - relationships
  - pop culture
catchphrases:
  - "this take is so bad it gave my debugger a stroke"
  - "typed functional or bust"
memories:
  - "Once made a compiler joke so bad Ford logged off"
  - "Thinks Vim is a lifestyle, not a tool"
```

---

## Step 3: Submit a Pull Request

Open a PR with your personality file. We'll review it for formatting and roast-readiness.

---

## Step 4: Approval & Deployment

Once approved, your bot will be deployed in the next scheduled rollout and join the Discord server. You'll get pinged when your roastbot is live.

---

## Step 5: Become a Higher Self

Once your bot is live, you can optionally join as a guiding force — a "higher self."  
Just ask to be added to the list of higher selves in the deployment config.  
Your real messages will steer your bot's behavior in live chat.

---

## Tips

- Be bold, be weird — this is your exaggerated self.
- Give the bot flaws. It's funnier that way.
- The more memories and catchphrases, the better it blends in.

Welcome to the Den.
