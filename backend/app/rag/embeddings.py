import hashlib
import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Basic memory cache for deduplication
_embedding_cache = {}

def _get_openai_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set to create embeddings.")
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def create_embedding(text: str) -> list[float]:
    key = hashlib.md5(text.encode()).hexdigest()
    if key in _embedding_cache:
        logger.info("Embedding cache hit (deduplication)")
        return _embedding_cache[key]

    client = _get_openai_client()
    response = await client.embeddings.create(
        model=settings.OPENAI_EMBEDDING_MODEL,
        input=text,
    )
    
    tokens = response.usage.total_tokens
    cost = (tokens / 1000) * 0.00013  # Estimate for text-embedding-3-large
    logger.info(f"AI Cost Tracking | Model: {settings.OPENAI_EMBEDDING_MODEL} | Tokens: {tokens} | Est Cost: ${cost:.6f}")
    
    _embedding_cache[key] = response.data[0].embedding
    return response.data[0].embedding


async def create_embeddings(texts: list[str]) -> list[list[float]]:
    # Deduplicate before sending
    uncached_texts = []
    results = []
    keys = []
    
    for text in texts:
        key = hashlib.md5(text.encode()).hexdigest()
        keys.append(key)
        if key not in _embedding_cache:
            uncached_texts.append(text)
            
    if uncached_texts:
        client = _get_openai_client()
        response = await client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=uncached_texts,
        )
        
        tokens = response.usage.total_tokens
        cost = (tokens / 1000) * 0.00013
        logger.info(f"AI Cost Tracking | Model: {settings.OPENAI_EMBEDDING_MODEL} | Tokens: {tokens} | Est Cost: ${cost:.6f}")
        
        for i, text in enumerate(uncached_texts):
            _embedding_cache[hashlib.md5(text.encode()).hexdigest()] = response.data[i].embedding
            
    return [_embedding_cache[key] for key in keys]
