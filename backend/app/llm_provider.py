"""Central LLM provider — swap backend by setting LLM_PROVIDER in .env."""

import logging
from functools import lru_cache

from .config import settings

logger = logging.getLogger("nova-agent")


@lru_cache(maxsize=1)
def get_llm():
    """Return a LangChain BaseChatModel for the configured provider.

    Supports: openai | gemini | ollama (set LLM_PROVIDER in .env).
    """
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        logger.info("[LLM] Provider: openai (%s)", settings.openai_model)
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        logger.info("[LLM] Provider: gemini (%s)", settings.gemini_chat_model)
        return ChatGoogleGenerativeAI(
            model=settings.gemini_chat_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.3,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        logger.info("[LLM] Provider: ollama (%s)", settings.ollama_model)
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.3,
        )

    raise ValueError(
        f"LLM_PROVIDER inválido: {provider!r}. Opciones: openai, gemini, ollama"
    )


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents using the configured provider."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            input=texts,
            model=settings.openai_embedding_model,
        )
        return [e.embedding for e in response.data]

    if provider in ("gemini", "ollama"):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        embeddings = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            result = client.models.embed_content(
                model=f"models/{settings.gemini_embedding_model}",
                contents=batch,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
            )
            embeddings.extend([e.values for e in result.embeddings])
        return embeddings

    raise ValueError(f"No hay embedder para provider: {provider!r}")


def embed_query(query: str) -> list[float]:
    """Embed a single query using the configured provider."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            input=[query],
            model=settings.openai_embedding_model,
        )
        return response.data[0].embedding

    if provider in ("gemini", "ollama"):
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=settings.gemini_api_key)
        result = client.models.embed_content(
            model=f"models/{settings.gemini_embedding_model}",
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values

    raise ValueError(f"No hay embedder para provider: {provider!r}")
