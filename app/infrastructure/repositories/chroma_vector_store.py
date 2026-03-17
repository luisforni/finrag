import uuid

import chromadb
from chromadb import AsyncClientAPI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.interfaces.vector_store import AbstractVectorStore
from app.domain.models.query import SourceChunk

logger = get_logger(__name__)
settings = get_settings()


class ChromaVectorStore(AbstractVectorStore):
    def __init__(self, client: AsyncClientAPI, collection_name: str) -> None:
        self._client = client
        self._collection_name = collection_name
        self._collection = None

    async def _get_collection(self):
        if self._collection is None:
            self._collection = await self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    async def add_chunks(
        self,
        document_id: uuid.UUID,
        document_filename: str,
        chunks: list[str],
    ) -> int:
        collection = await self._get_collection()
        ids = [f"{document_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {"document_id": str(document_id), "document_filename": document_filename, "chunk_index": i}
            for i in range(len(chunks))
        ]
        await collection.add(ids=ids, documents=chunks, metadatas=metadatas)
        logger.info("chunks_added", document_id=str(document_id), count=len(chunks))
        return len(chunks)

    async def similarity_search(
        self,
        query: str,
        top_k: int,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[SourceChunk]:
        collection = await self._get_collection()

        where = None
        if document_ids:
            if len(document_ids) == 1:
                where = {"document_id": str(document_ids[0])}
            else:
                where = {"document_id": {"$in": [str(d) for d in document_ids]}}

        results = await collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks: list[SourceChunk] = []
        if not results["documents"] or not results["documents"][0]:
            return chunks

        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(
                SourceChunk(
                    document_id=uuid.UUID(meta["document_id"]),
                    document_filename=meta["document_filename"],
                    chunk_index=meta["chunk_index"],
                    content=doc,
                    score=1.0 - dist,  # cosine similarity
                )
            )
        return chunks

    async def delete_document(self, document_id: uuid.UUID) -> bool:
        collection = await self._get_collection()
        results = await collection.get(
            where={"document_id": str(document_id)},
            include=[],
        )
        ids = results.get("ids", [])
        if ids:
            await collection.delete(ids=ids)
            logger.info("document_chunks_deleted", document_id=str(document_id), count=len(ids))
        return True
