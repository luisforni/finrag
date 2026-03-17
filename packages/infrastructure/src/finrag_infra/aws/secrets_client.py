import json

import boto3
from botocore.exceptions import ClientError

from finrag_core.core.logging import get_logger

logger = get_logger(__name__)


def fetch_secret(secret_name: str, region: str = "us-east-1") -> dict:
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
    except ClientError as exc:
        logger.error("secrets_manager_error", secret=secret_name, error=str(exc))
        raise
    return json.loads(response.get("SecretString", "{}"))
