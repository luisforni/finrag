from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger
from app.domain.services.rag_service import LLMClientProtocol

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a financial document analysis assistant for a bank.
Answer the user's question using ONLY the provided context from financial documents.
If the context does not contain enough information, say so clearly.
Be precise, cite the source when relevant, and never fabricate numbers or facts."""


class OpenAILLMClient(LLMClientProtocol):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(self, question: str, context: str) -> tuple[str, int]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ]

        response = await self._client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            temperature=0.1,
            max_tokens=1500,
        )

        answer = response.choices[0].message.content or ""
        tokens_used = response.usage.total_tokens if response.usage else 0

        logger.info("llm_response", model=settings.llm_model, tokens=tokens_used)
        return answer, tokens_used
