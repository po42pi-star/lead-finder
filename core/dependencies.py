from core.config.settings import Settings, get_settings
from core.rag.cache import RetrievalCache
from core.rag.chroma_store import ChromaStore
from core.rag.chunker import MarkdownChunker
from core.rag.document_loader import DocumentLoader
from core.rag.embeddings import EmbeddingService
from core.rag.intent_classifier import IntentClassifier
from core.rag.retrieval import RetrievalPipeline


def get_chroma_store() -> ChromaStore:
    return ChromaStore(get_settings())


def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_settings())


def get_document_loader() -> DocumentLoader:
    return DocumentLoader(get_settings())


def get_markdown_chunker() -> MarkdownChunker:
    return MarkdownChunker(get_settings())


def get_retrieval_cache() -> RetrievalCache:
    return RetrievalCache(get_settings())


def get_intent_classifier() -> IntentClassifier:
    return IntentClassifier(get_settings())


def get_retrieval_pipeline() -> RetrievalPipeline:
    settings = get_settings()
    return RetrievalPipeline(
        settings=settings,
        chroma=get_chroma_store(),
        embeddings=get_embedding_service(),
        intent_classifier=get_intent_classifier(),
        cache=get_retrieval_cache(),
    )


def clear_dependency_cache() -> None:
    pass
