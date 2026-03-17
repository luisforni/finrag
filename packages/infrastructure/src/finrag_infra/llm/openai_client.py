from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from finrag_core.core.config import get_settings
from finrag_core.core.logging import get_logger
from finrag_core.domain.interfaces.llm_client import AbstractLLMClient

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_PROMPT = """You are a financial document analysis assistant for a bank.
Answer the user's question using ONLY the provided context from financial documents.
If the context does not contain enough information, say so clearly.
Be precise, cite the source when relevant, and never fabricate numbers or facts."""


class OpenAILLMClient(AbstractLLMClient):
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def generate(self, question: str, context: str) -> tuple[str, int]:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
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
