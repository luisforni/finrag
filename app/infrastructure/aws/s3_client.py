import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import boto3
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.interfaces.object_storage import AbstractObjectStorage

logger = get_logger(__name__)
settings = get_settings()

_executor = ThreadPoolExecutor(max_workers=4)


class S3ObjectStorage(AbstractObjectStorage):
    def __init__(self) -> None:
        self._s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._bucket = settings.s3_bucket_name

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _executor,
            partial(
                self._s3.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            ),
        )
        logger.info("s3_upload", key=key, size=len(data))
        return key

    async def download(self, key: str) -> bytes:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            _executor,
            partial(self._s3.get_object, Bucket=self._bucket, Key=key),
        )
        return response["Body"].read()

    async def delete(self, key: str) -> bool:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                _executor,
                partial(self._s3.delete_object, Bucket=self._bucket, Key=key),
            )
            logger.info("s3_delete", key=key)
            return True
        except ClientError as exc:
            logger.error("s3_delete_failed", key=key, error=str(exc))
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
