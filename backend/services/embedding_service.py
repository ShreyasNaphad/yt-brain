from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        # TF-IDF vectorizer configuration
        self.vectorizer = TfidfVectorizer(max_features=500, stop_words='english')
        self._fitted = False
        self._corpus = []
        logger.info("Initialized TF-IDF Embedding Service")
    
    def fit(self, texts: list[str]):
        """
        Fit the vectorizer on the provided texts (corpus).
        This is necessary before embedding any text.
        """
        try:
            self._corpus = texts
            self.vectorizer.fit(texts)
            self._fitted = True
            logger.info(f"Fitted TF-IDF on {len(texts)} chunks")
        except Exception as e:
            logger.error(f"Error fitting TF-IDF: {e}")

    def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string.
        Be sure fit() has been called or we will fit on this single text (not ideal for retrieval).
        """
        if not self._fitted:
            logger.warning("Vectorizer not fitted. Fitting on single text (fallback).")
            self.vectorizer.fit([text])
            self._fitted = True
            
        try:
            vec = self.vectorizer.transform([text]).toarray()[0]
            return vec.tolist()
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            return []
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts.
        """
        # If not fitted, we can fit on this batch? 
        # Usually we want to fit on the DOCUMENT chunks, then transform QUERY.
        # But for the initial document embedding, we call fit on chunks.
        if not self._fitted:
             self.fit(texts)

        try:
            return self.vectorizer.transform(texts).toarray().tolist()
        except Exception as e:
            logger.error(f"Error embedding batch: {e}")
            return []

# Singleton instance
embedding_service = EmbeddingService()
