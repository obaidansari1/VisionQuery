"""CLIP embeddings, shared by the Celery worker (frames) and the search API (text queries).

Both images and text are embedded into the same 512-dim vector space by the same
CLIP model, so a text query can be compared directly against stored frame embeddings
with cosine similarity. The model is loaded once per process and cached.
"""
import functools
import logging

logger = logging.getLogger(__name__)

MODEL_NAME = "clip-ViT-B-32"
EMBEDDING_DIMENSIONS = 512


class ClipEmbedder:
    def __init__(self, model):
        self._model = model

    def embed_image(self, pil_image) -> list[float]:
        vector = self._model.encode(pil_image, convert_to_numpy=True, normalize_embeddings=True)
        return vector.tolist()

    def embed_text(self, text: str) -> list[float]:
        vector = self._model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
        return vector.tolist()


@functools.lru_cache(maxsize=1)
def get_embedder() -> ClipEmbedder:
    """Load (and cache) the CLIP model. First call downloads weights if not cached locally."""
    from sentence_transformers import SentenceTransformer

    logger.info("Loading CLIP model %s (cached for the life of this process)", MODEL_NAME)
    model = SentenceTransformer(MODEL_NAME)
    return ClipEmbedder(model)
