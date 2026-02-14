import numpy as np
import json
import os

# Lazy-load heavy dependencies
_encoder = None
_faiss = None
vector_dim = 384

def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer
            _encoder = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Sentence Transformer model loaded.")
        except Exception as e:
            print(f"⚠️ SentenceTransformer not available: {e}")
    return _encoder

def _get_faiss():
    global _faiss
    if _faiss is None:
        try:
            import faiss as _f
            _faiss = _f
        except ImportError:
            print("⚠️ FAISS not available.")
    return _faiss

class SpatialMemory:
    def __init__(self, index_path="data/memory/spatial_index.faiss"):
        self.index_path = index_path
        self.metadata = []
        self.index = None
        self._initialized = False

    def _ensure_init(self):
        """Lazy-init: only load FAISS index when first needed."""
        if self._initialized:
            return
        self._initialized = True
        
        faiss = _get_faiss()
        if faiss is None:
            return
            
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
            meta_path = self.index_path.replace(".faiss", ".json")
            if os.path.exists(meta_path):
                with open(meta_path, "r") as f:
                    self.metadata = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(vector_dim)

    def add_observation(self, text: str, meta: dict):
        self._ensure_init()
        encoder = _get_encoder()
        faiss = _get_faiss()
        
        if encoder is None or faiss is None or self.index is None:
            print("⚠️ Cannot add observation: ML models not loaded.")
            return
            
        embedding = encoder.encode([text])
        faiss.normalize_L2(embedding)
        self.index.add(embedding)
        self.metadata.append({"text": text, **meta})
        
    def search(self, query: str, k: int = 3):
        self._ensure_init()
        encoder = _get_encoder()
        faiss = _get_faiss()
        
        if encoder is None or faiss is None or self.index is None:
            return []
            
        query_vec = encoder.encode([query])
        faiss.normalize_L2(query_vec)
        
        distances, indices = self.index.search(query_vec, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.metadata):
                item = self.metadata[idx]
                results.append({
                    "score": float(distances[0][i]),
                    "description": item["text"],
                    "metadata": item
                })
        return results

    def save(self):
        faiss = _get_faiss()
        if faiss is None or self.index is None:
            return
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.index_path.replace(".faiss", ".json"), "w") as f:
            json.dump(self.metadata, f)
