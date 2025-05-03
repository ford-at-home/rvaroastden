#!/usr/bin/env python3
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
    aws_cloudwatch as cloudwatch
)

from constructs import Construct

class SimulchaosStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create CloudWatch dashboard
        dashboard = cloudwatch.Dashboard(self, "SimulchaosDashboard",
            dashboard_name="SimulchaosBot"
        )

        # Import existing secret - DO NOT create with hardcoded value
        discord_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "DiscordTokenSecret",
            secret_name="simulchaos/discord"
        )

        lambda_role = iam.Role(self, "SimulchaosLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
        )

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue"],
            resources=[discord_secret.secret_arn]
        ))

        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # Add CloudWatch metrics permissions
        lambda_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "cloudwatch:PutMetricData",
                "cloudwatch:GetMetricData",
                "cloudwatch:GetMetricStatistics"
            ],
            resources=["*"]
        ))

        memory_table = dynamodb.Table(self, "SimulchaosMemoryTable",
            table_name="SimulchaosMemory",
            partition_key={"name": "bot_name", "type": dynamodb.AttributeType.STRING},
            sort_key={"name": "timestamp", "type": dynamodb.AttributeType.STRING},
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True
        )

        memory_table.grant_read_write_data(lambda_role)

        bot_lambda = _lambda.Function(self, "SimulchaosBotHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="bot.handler",
            code=_lambda.Code.from_asset("bot"),
            environment={
                "DISCORD_SECRET_ARN": discord_secret.secret_arn,
                "MEMORY_TABLE": memory_table.table_name,
                "LOG_LEVEL": "INFO"
            },
            timeout=cdk.Duration.seconds(30),
            role=lambda_role,
            log_retention=logs.RetentionDays.ONE_WEEK,
            tracing=_lambda.Tracing.ACTIVE
        )

        # Add CloudWatch metrics to dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Bot Metrics",
                left=[
                    bot_lambda.metric("Invocations"),
                    bot_lambda.metric("Errors"),
                    bot_lambda.metric("Duration")
                ]
            ),
            cloudwatch.GraphWidget(
                title="Memory Operations",
                left=[
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="MemorySaved",
                        statistic="Sum"
                    ),
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="MemoryLoaded",
                        statistic="Sum"
                    )
                ]
            ),
            cloudwatch.GraphWidget(
                title="Claude Performance",
                left=[
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeResponseTime",
                        statistic="Average"
                    ),
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeSuccess",
                        statistic="Sum"
                    ),
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeError",
                        statistic="Sum"
                    )
                ]
            )
        )

app = cdk.App()
SimulchaosStack(app, "SimulchaosStack")
app.synth()
