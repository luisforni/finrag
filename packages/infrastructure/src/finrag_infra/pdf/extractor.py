import io

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from finrag_core.core.config import get_settings
from finrag_core.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class PDFTextExtractor:
    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def extract_and_chunk(self, file_data: bytes) -> list[str]:
        reader = PdfReader(io.BytesIO(file_data))
        full_text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not full_text:
            raise ValueError("Could not extract text from PDF")
        chunks = self._splitter.split_text(full_text)
        logger.info("pdf_extracted", pages=len(reader.pages), chunks=len(chunks))
        return chunks
