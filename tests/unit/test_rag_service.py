import uuid

import pytest

from finrag_core.domain.models.query import QueryRequest, QueryResponse
from finrag_core.services.rag_service import RAGService


@pytest.fixture
def service(mock_vector_store, mock_llm, mock_query_log_repo):
    return RAGService(
        vector_store=mock_vector_store,
        llm_client=mock_llm,
        query_log_repo=mock_query_log_repo,
    )


class TestRAGQuery:
    async def test_returns_answer_with_sources(
        self,
        service,
        mock_vector_store,
        mock_llm,
        mock_query_log_repo,
        sample_source,
    ):
        mock_vector_store.similarity_search.return_value = [sample_source]
        mock_llm.generate.return_value = ("El ratio es 145%.", 120)
        mock_query_log_repo.create.return_value = None

        response = await service.query(
            QueryRequest(question="¿Cuál es el ratio de cobertura?"), uuid.uuid4()
        )

        assert isinstance(response, QueryResponse)
        assert response.answer == "El ratio es 145%."
        assert len(response.sources) == 1
        assert response.tokens_used == 120
        mock_query_log_repo.create.assert_called_once()

    async def test_no_sources_skips_llm(
        self,
        service,
        mock_vector_store,
        mock_llm,
        mock_query_log_repo,
    ):
        mock_vector_store.similarity_search.return_value = []
        mock_query_log_repo.create.return_value = None

        response = await service.query(
            QueryRequest(question="¿Pregunta sin contexto alguno?"), uuid.uuid4()
        )

        assert "No relevant context" in response.answer
        assert response.tokens_used == 0
        mock_llm.generate.assert_not_called()
        mock_query_log_repo.create.assert_called_once()

    async def test_persists_query_log_with_user_id(
        self,
        service,
        mock_vector_store,
        mock_llm,
        mock_query_log_repo,
        sample_source,
    ):
        mock_vector_store.similarity_search.return_value = [sample_source]
        mock_llm.generate.return_value = ("respuesta", 80)
        mock_query_log_repo.create.return_value = None

        user_id = uuid.uuid4()
        await service.query(QueryRequest(question="Pregunta de prueba aquí."), user_id)

        log = mock_query_log_repo.create.call_args[0][0]
        assert log.user_id == user_id
        assert log.tokens_used == 80
        assert log.sources_count == 1

    def test_build_context_formats_sources(self, service, sample_source):
        context = service._build_context([sample_source])
        assert "Source 1" in context
        assert sample_source.document_filename in context
        assert sample_source.content in context
