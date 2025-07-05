#!/usr/bin/env python3
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
    aws_applicationautoscaling as autoscaling,
    aws_ecs_patterns as ecs_patterns,
    Duration,
)

from constructs import Construct


class SimulchaosStack(cdk.Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Create CloudWatch dashboard
        dashboard = cloudwatch.Dashboard(
            self, "SimulchaosDashboard", dashboard_name="SimulchaosBot"
        )

        # Import existing secret - DO NOT create with hardcoded value
        discord_secret = secretsmanager.Secret.from_secret_name_v2(
            self, "DiscordTokenSecret", secret_name="simulchaos/discord"
        )

        # Create VPC for Fargate (or use existing)
        vpc = ec2.Vpc(
            self,
            "SimulchaosVPC",
            max_azs=2,
            nat_gateways=1,  # Cost optimization - only 1 NAT gateway
        )

        # Create ECS Cluster
        cluster = ecs.Cluster(
            self, "SimulchaosCluster", vpc=vpc, cluster_name="simulchaos-bot-cluster"
        )

        # Create DynamoDB table for memory storage
        memory_table = dynamodb.Table(
            self,
            "SimulchaosMemoryTable",
            table_name="SimulchaosMemory",
            partition_key={"name": "bot_name", "type": dynamodb.AttributeType.STRING},
            sort_key={"name": "timestamp", "type": dynamodb.AttributeType.STRING},
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=True,
        )

        # Create SQS queue for async message processing
        message_queue = sqs.Queue(
            self,
            "SimulchaosMessageQueue",
            queue_name="simulchaos-messages",
            visibility_timeout=Duration.seconds(300),  # 5 minutes for processing
            retention_period=Duration.days(1),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=sqs.Queue(
                    self, "SimulchaosDLQ", queue_name="simulchaos-messages-dlq"
                ),
            ),
        )

        # Create task role for Fargate container
        task_role = iam.Role(
            self,
            "SimulchaosTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Role for Simulchaos Discord bot container",
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

        # Create execution role for Fargate
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

        # Grant secret access to execution role for container startup
        execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["secretsmanager:GetSecretValue"],
                resources=[discord_secret.secret_arn],
            )
        )

        # Create log group for container
        log_group = logs.LogGroup(
            self,
            "SimulchaosLogGroup",
            log_group_name="/ecs/simulchaos-bot",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # Create Fargate task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "SimulchaosTaskDef",
            memory_limit_mib=512,  # 0.5 GB
            cpu=256,  # 0.25 vCPU
            task_role=task_role,
            execution_role=execution_role,
        )

        # Build Docker image from local Dockerfile
        docker_image = ecr_assets.DockerImageAsset(
            self, "SimulchaosBotImage", directory=".", file="Dockerfile"
        )

        # Add container to task definition
        container = task_definition.add_container(
            "discord-bot",
            image=ecs.ContainerImage.from_docker_image_asset(docker_image),
            environment={
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
                stream_prefix="discord-bot", log_group=log_group
            ),
            health_check=ecs.HealthCheck(
                command=[
                    "CMD-SHELL",
                    "python -c 'import requests; requests.get(\"http://localhost:8080/health\")'",
                ],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(10),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )

        # Create Fargate service
        fargate_service = ecs.FargateService(
            self,
            "SimulchaosFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,  # Only need 1 instance for Discord bot
            service_name="simulchaos-bot-service",
        )

        # Set up auto-scaling (optional - for high availability)
        scaling = fargate_service.auto_scale_task_count(
            min_capacity=1, max_capacity=2  # Allow scaling to 2 for high availability
        )

        # Scale based on CPU utilization
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
            scale_in_cooldown=Duration.seconds(300),
            scale_out_cooldown=Duration.seconds(60),
        )

        # Create Lambda role for message processor
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

        # Grant Lambda access to Discord secret
        discord_secret.grant_read(lambda_role)

        # Create Lambda layer for personalities
        personalities_layer = _lambda.LayerVersion(
            self,
            "PersonalitiesLayer",
            code=_lambda.Code.from_asset("personalities"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_11],
            description="Bot personality definitions",
        )

        # Create log group for Lambda
        lambda_log_group = logs.LogGroup(
            self,
            "MessageProcessorLogGroup",
            log_group_name="/aws/lambda/message-processor",
            retention=logs.RetentionDays.ONE_WEEK,
        )

        # Create Lambda function for message processing
        message_processor = _lambda.Function(
            self,
            "MessageProcessor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="message_processor.handler",
            code=_lambda.Code.from_asset("lambda"),
            environment={"MEMORY_TABLE": memory_table.table_name, "LOG_LEVEL": "INFO"},
            timeout=Duration.seconds(300),  # 5 minutes for Claude processing
            memory_size=512,
            role=lambda_role,
            log_group=lambda_log_group,
            tracing=_lambda.Tracing.ACTIVE,
            layers=[personalities_layer],
        )

        # Add SQS trigger to Lambda
        message_processor.add_event_source(
            lambda_event_sources.SqsEventSource(
                message_queue, batch_size=1  # Process one message at a time
            )
        )

        # Add CloudWatch metrics to dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Container Health",
                left=[
                    fargate_service.metric_cpu_utilization(),
                    fargate_service.metric_memory_utilization(),
                ],
            ),
            cloudwatch.GraphWidget(
                title="Message Processing",
                left=[
                    message_queue.metric_approximate_number_of_messages_visible(),
                    message_queue.metric_approximate_number_of_messages_not_visible(),
                    message_processor.metric("Invocations"),
                    message_processor.metric("Errors"),
                ],
            ),
            cloudwatch.GraphWidget(
                title="Claude Performance",
                left=[
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeResponseTime",
                        statistic="Average",
                    ),
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeSuccess",
                        statistic="Sum",
                    ),
                    cloudwatch.Metric(
                        namespace="RvarOastDen",
                        metric_name="ClaudeError",
                        statistic="Sum",
                    ),
                ],
            ),
        )

        # Outputs
        cdk.CfnOutput(
            self,
            "ClusterName",
            value=cluster.cluster_name,
            description="ECS Cluster Name",
        )

        cdk.CfnOutput(
            self,
            "ServiceName",
            value=fargate_service.service_name,
            description="ECS Service Name",
        )

        cdk.CfnOutput(
            self, "QueueUrl", value=message_queue.queue_url, description="SQS Queue URL"
        )


app = cdk.App()
SimulchaosStack(app, "SimulchaosStack")
app.synth()
