#!/usr/bin/env python3
"""CDK Stack for multiple personality bots"""
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_secretsmanager as secretsmanager,
    aws_iam as iam,
    aws_logs as logs,
    aws_dynamodb as dynamodb,
    aws_cloudwatch as cloudwatch,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_event_sources,
    Duration,
)
from constructs import Construct


class SimulchaosMultiBotStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Bot configurations
        BOT_CONFIGS = {
            "FordBot": {
                "secret_name": "simulchaos/discord-ford",
                "cpu": 256,
                "memory": 512,
            },
            "AprilBot": {
                "secret_name": "simulchaos/discord-april",
                "cpu": 256,
                "memory": 512,
            },
            "AdamBot": {
                "secret_name": "simulchaos/discord-adam",
                "cpu": 256,
                "memory": 512,
            },
        }

        # Create CloudWatch dashboard
        dashboard = cloudwatch.Dashboard(
            self, "SimulchaosMultiBotDashboard", dashboard_name="SimulchaosMultiBot"
        )

        # Create VPC for Fargate
        vpc = ec2.Vpc(self, "SimulchaosVPC", max_azs=2, nat_gateways=1)

        # Create ECS Cluster
        cluster = ecs.Cluster(
            self,
            "SimulchaosCluster",
            vpc=vpc,
            cluster_name="simulchaos-multibot-cluster",
        )

        # Create shared DynamoDB table for memory storage
        memory_table = dynamodb.Table(
            self,
            "SimulchaosMemoryTable",
            table_name="SimulchaosMemory",
            partition_key={"name": "bot_name", "type": dynamodb.AttributeType.STRING},
            sort_key={"name": "timestamp", "type": dynamodb.AttributeType.STRING},
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
        )

        # Create shared SQS queue for async message processing
        message_queue = sqs.Queue(
            self,
            "SimulchaosMessageQueue",
            queue_name="simulchaos-messages",
            visibility_timeout=Duration.seconds(300),
            retention_period=Duration.days(1),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=sqs.Queue(
                    self, "SimulchaosDLQ", queue_name="simulchaos-messages-dlq"
                ),
            ),
        )

        # Build Docker image for personality bots
        docker_image = ecr_assets.DockerImageAsset(
            self, "SimulchaosBotImage", directory=".", file="Dockerfile.personality"
        )

        # Create execution role for all bots
        execution_role = iam.Role(
            self,
            "SimulchaosExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )

        # Create services for each bot
        for bot_name, config in BOT_CONFIGS.items():
            # Import bot-specific secret
            discord_secret = secretsmanager.Secret.from_secret_name_v2(
                self, f"{bot_name}DiscordSecret", secret_name=config["secret_name"]
            )

            # Grant secret access to execution role
            discord_secret.grant_read(execution_role)

            # Create task role for this bot
            task_role = iam.Role(
                self,
                f"{bot_name}TaskRole",
                assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                description=f"Role for {bot_name} Discord bot container",
            )

            # Grant permissions to task role
            task_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["secretsmanager:GetSecretValue"],
                    resources=[discord_secret.secret_arn],
                )
            )

            task_role.add_to_policy(
                iam.PolicyStatement(
                    actions=["sqs:SendMessage", "sqs:GetQueueUrl"],
                    resources=[message_queue.queue_arn],
                )
            )

            task_role.add_to_policy(
                iam.PolicyStatement(
                    actions=[
                        "cloudwatch:PutMetricData",
                        "cloudwatch:GetMetricData",
                        "cloudwatch:GetMetricStatistics",
                    ],
                    resources=["*"],
                )
            )

            memory_table.grant_read_write_data(task_role)

            # Create log group for this bot
            log_group = logs.LogGroup(
                self,
                f"{bot_name}LogGroup",
                log_group_name=f"/ecs/simulchaos-{bot_name.lower()}",
                retention=logs.RetentionDays.ONE_WEEK,
            )

            # Create Fargate task definition
            task_definition = ecs.FargateTaskDefinition(
                self,
                f"{bot_name}TaskDef",
                memory_limit_mib=config["memory"],
                cpu=config["cpu"],
                task_role=task_role,
                execution_role=execution_role,
            )

            # Add container to task definition
            container = task_definition.add_container(
                f"{bot_name.lower()}-container",
                image=ecs.ContainerImage.from_docker_image_asset(docker_image),
                environment={
                    "BOT_PERSONALITY": bot_name,
                    "SQS_QUEUE_URL": message_queue.queue_url,
                    "MEMORY_TABLE": memory_table.table_name,
                    "LOG_LEVEL": "INFO",
                    "AWS_DEFAULT_REGION": self.region,
                },
                secrets={
                    "DISCORD_TOKEN": ecs.Secret.from_secrets_manager(
                        discord_secret, "DISCORD_TOKEN"
                    )
                },
                logging=ecs.LogDriver.aws_logs(
                    stream_prefix=bot_name.lower(), log_group=log_group
                ),
                command=["python", "bot_container_personality.py"],
                health_check=ecs.HealthCheck(
                    command=[
                        "CMD-SHELL",
                        "curl -f http://localhost:8080/health || exit 1",
                    ],
                    interval=Duration.seconds(30),
                    timeout=Duration.seconds(10),
                    retries=3,
                    start_period=Duration.seconds(60),
                ),
            )

            # Create Fargate service for this bot
            fargate_service = ecs.FargateService(
                self,
                f"{bot_name}FargateService",
                cluster=cluster,
                task_definition=task_definition,
                desired_count=1,
                service_name=f"simulchaos-{bot_name.lower()}-service",
            )

            # Add to dashboard
            dashboard.add_widgets(
                cloudwatch.GraphWidget(
                    title=f"{bot_name} Health",
                    left=[
                        fargate_service.metric_cpu_utilization(),
                        fargate_service.metric_memory_utilization(),
                    ],
                )
            )

        # Create Lambda for message processing (shared by all bots)
        lambda_role = iam.Role(
            self,
            "SimulchaosLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"])
        )

        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cloudwatch:PutMetricData",
                    "cloudwatch:GetMetricData",
                    "cloudwatch:GetMetricStatistics",
                ],
                resources=["*"],
            )
        )

        memory_table.grant_read_write_data(lambda_role)
        message_queue.grant_consume_messages(lambda_role)

        # Grant Lambda access to all Discord secrets for message updates
        for bot_name, config in BOT_CONFIGS.items():
            discord_secret = secretsmanager.Secret.from_secret_name_v2(
                self, f"{bot_name}LambdaSecret", secret_name=config["secret_name"]
            )
            discord_secret.grant_read(lambda_role)

        # Create Lambda layer for personalities
        personalities_layer = _lambda.LayerVersion(
            self,
            "PersonalitiesLayer",
            code=_lambda.Code.from_asset("personalities"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Bot personality definitions",
        )

        # Create Lambda function for message processing
        message_processor = _lambda.Function(
            self,
            "MessageProcessor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="message_processor.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={"MEMORY_TABLE": memory_table.table_name, "LOG_LEVEL": "INFO"},
            timeout=Duration.seconds(300),
            memory_size=512,
            role=lambda_role,
            tracing=_lambda.Tracing.ACTIVE,
            layers=[personalities_layer],
        )

        # Add SQS trigger to Lambda
        message_processor.add_event_source(
            lambda_event_sources.SqsEventSource(message_queue, batch_size=1)
        )

        # Outputs
        cdk.CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
            description="ECS Cluster Name",
        )

        cdk.CfnOutput(
            self, "QueueUrl", value=message_queue.queue_url, description="SQS Queue URL"
        )

        for bot_name in BOT_CONFIGS.keys():
            cdk.CfnOutput(
                self,
                f"{bot_name}ServiceName",
                value=f"simulchaos-{bot_name.lower()}-service",
                description=f"{bot_name} ECS Service Name",
            )


app = cdk.App()
SimulchaosMultiBotStack(app, "SimulchaosMultiBotStack")
app.synth()
