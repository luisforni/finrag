from abc import ABC, abstractmethod


class AbstractObjectStorage(ABC):
    """Port: defines what the domain needs from object storage."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        ...
