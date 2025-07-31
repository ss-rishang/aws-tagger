"""
Simple AWS Client Management
"""

import boto3
from .utils import logger


def get_clients(region: str) -> dict:
    """Get all AWS clients - simple and clean"""

    logger.debug(f"Initializing AWS clients for region: {region}")

    try:
        # Get account ID once
        sts = boto3.client("sts")
        account_id = sts.get_caller_identity()["Account"]
        logger.debug(f"Using AWS account: {account_id}")

        return {
            # Core services
            "cloudtrail": boto3.client("cloudtrail", region_name=region),
            "ec2": boto3.client("ec2", region_name=region),
            "s3": boto3.client("s3"),
            "rds": boto3.client("rds", region_name=region),
            "lambda": boto3.client("lambda", region_name=region),
            "eks": boto3.client("eks", region_name=region),
            "elbv2": boto3.client("elbv2", region_name=region),
            # Database services
            "dynamodb": boto3.client("dynamodb", region_name=region),
            "redshift": boto3.client("redshift", region_name=region),
            # Security services
            "iam": boto3.client("iam"),
            "kms": boto3.client("kms", region_name=region),
            "secretsmanager": boto3.client("secretsmanager", region_name=region),
            "cognito-idp": boto3.client("cognito-idp", region_name=region),
            "cognito-identity": boto3.client("cognito-identity", region_name=region),
            # Messaging services
            "sns": boto3.client("sns", region_name=region),
            "sqs": boto3.client("sqs", region_name=region),
            # Monitoring services
            "cloudwatch": boto3.client("cloudwatch", region_name=region),
            "cloudwatch-logs": boto3.client("logs", region_name=region),
            # Networking services
            "route53": boto3.client("route53"),
            "apigateway": boto3.client("apigateway", region_name=region),
            "cloudfront": boto3.client("cloudfront"),
            # Container services
            "ecs": boto3.client("ecs", region_name=region),
            "ecr": boto3.client("ecr", region_name=region),
            # Workflow & Management
            "stepfunctions": boto3.client("stepfunctions", region_name=region),
            "cloudformation": boto3.client("cloudformation", region_name=region),
            "glue": boto3.client("glue", region_name=region),
            # Storage & File systems
            "efs": boto3.client("efs", region_name=region),
            # Analytics & Search
            "opensearch": boto3.client("opensearch", region_name=region),
            # AI/ML services
            "bedrock": boto3.client("bedrock", region_name=region),
            # Web & Mobile
            "amplify": boto3.client("amplify", region_name=region),
            # Metadata
            "region": region,
            "account_id": account_id,
        }
    except Exception as e:
        logger.error(f"Failed to initialize AWS clients: {e}")
        raise
