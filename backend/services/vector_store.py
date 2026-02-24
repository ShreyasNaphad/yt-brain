import numpy as np
from collections import defaultdict

class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._chunks = defaultdict(list)  # video_id -> list of chunk dicts
            # Chunk dict structure: {text, start_time, chunk_index, vector}
            cls._instance.client = True # Mock client for checks in main.py if any (though we remove them)
            cls._instance.collection_name = "yt_brain"
        return cls._instance
    
    def upsert_chunks(self, video_id: str, chunks: list):
        """
        Store chunks in memory.
        chunks: list of dicts, each must have 'vector' key with embedding.
        """
        self._chunks[video_id] = chunks
        return True
    
    def search(self, video_id: str, query_vector: list, top_k: int = 5) -> list:
        """
        Perform cosine similarity search in memory.
        """
        if video_id not in self._chunks:
            return []
            
        chunks = self._chunks[video_id]
        if not chunks:
            return []
            
        # Extract vectors from chunks
        # Assuming query_vector is list or numpy array
        query = np.array(query_vector)
        norm_query = np.linalg.norm(query)
        
        if norm_query == 0:
            return []
            
        scores = []
        for chunk in chunks:
            if 'vector' not in chunk:
                continue
                
            vec = np.array(chunk['vector'])
            norm_vec = np.linalg.norm(vec)
            
            if norm_vec == 0:
                similarity = 0.0
            else:
                similarity = float(np.dot(query, vec) / (norm_query * norm_vec))
                
            scores.append((similarity, chunk))
            
        # Sort by similarity descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return top_k chunks
        # Return top_k chunks
        return [c for _, c in scores[:top_k]]

# Global Singleton
vector_store = VectorStore()
