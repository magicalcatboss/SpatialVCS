import json
import os
import sys
from typing import Optional

# Python 3.14+ PEP 649 compat: pydantic v1 (used by chromadb) reads
# namespace["__annotations__"] which is None under deferred evaluation.
# Patch the metaclass once so that __annotate_func__ is evaluated eagerly.
if sys.version_info >= (3, 14):
    try:
        import pydantic.v1.main as _pv1_main

        _orig_mc_new = _pv1_main.ModelMetaclass.__new__

        def _patched_mc_new(mcs, name, bases, namespace, **kwargs):
            if namespace.get("__annotations__") is None:
                _af = namespace.get("__annotate_func__")
                if _af is not None:
                    try:
                        namespace["__annotations__"] = _af(1)
                    except Exception:
                        namespace["__annotations__"] = {}
            return _orig_mc_new(mcs, name, bases, namespace, **kwargs)

        _pv1_main.ModelMetaclass.__new__ = _patched_mc_new
    except Exception:
        pass

# Lazy-load heavy dependencies
_encoder = None
_chroma = None
vector_dim = 384


def _get_encoder():
    global _encoder
    if _encoder is None:
        try:
            from sentence_transformers import SentenceTransformer

            _encoder = SentenceTransformer("all-MiniLM-L6-v2")
            print("✅ Sentence Transformer model loaded.")
        except Exception as e:
            print(f"⚠️ SentenceTransformer not available: {e}")
    return _encoder


def _get_chroma():
    global _chroma
    if _chroma is None:
        try:
            import chromadb

            _chroma = chromadb
        except Exception as e:
            print(f"⚠️ ChromaDB not available: {e}")
    return _chroma


class SpatialMemory:
    def __init__(self, index_path: str = "data/memory/spatial_index.json"):
        # Keep old argument name compatibility, but use ChromaDB persist dir.
        self.index_path = index_path
        self.persist_dir = "data/chroma"
        self.metadata = []
        self.collection = None
        self._initialized = False
        self._id_counter = 0
        self._warned_not_ready = False

    def _ensure_init(self):
        """Lazy-init: only load Chroma collection when first needed."""
        if self._initialized:
            return
        self._initialized = True

        chroma = _get_chroma()
        if chroma is None:
            return

        os.makedirs(self.persist_dir, exist_ok=True)
        client = chroma.PersistentClient(path=self.persist_dir)
        self.collection = client.get_or_create_collection(name="spatial_memory")

        # Backfill local cache for compatibility with existing consumers.
        try:
            snapshot = self.collection.get(include=["metadatas", "documents"])
            docs = snapshot.get("documents", []) or []
            metas = snapshot.get("metadatas", []) or []
            self.metadata = []
            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
                self.metadata.append({"text": doc, **meta})
            self._id_counter = len(self.metadata)
        except Exception as e:
            print(f"⚠️ Failed to warm Chroma cache: {e}")

    def _serialize_meta(self, meta: dict):
        """Chroma metadata values should be scalar; stash nested values as JSON."""
        serialized = {}
        for key, value in meta.items():
            # Chroma metadata does not accept None; use empty string sentinel.
            if value is None:
                serialized[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            else:
                serialized[key] = json.dumps(value, ensure_ascii=False)
        return serialized

    def _deserialize_meta(self, meta: Optional[dict]):
        if not isinstance(meta, dict):
            return {}
        restored = {}
        for key, value in meta.items():
            if isinstance(value, str):
                try:
                    restored[key] = json.loads(value)
                    continue
                except Exception:
                    pass
            restored[key] = value
        return restored

    def add_observation(self, text: str, meta: dict):
        self._ensure_init()
        encoder = _get_encoder()

        if encoder is None or self.collection is None:
            if not self._warned_not_ready:
                print("⚠️ Cannot add observation: ML models/storage not loaded. (further warnings suppressed)")
                self._warned_not_ready = True
            return

        embedding = encoder.encode([text])[0]
        item_id = f"obs_{self._id_counter}"
        self._id_counter += 1

        serialized_meta = self._serialize_meta(meta)
        self.collection.add(
            ids=[item_id],
            documents=[text],
            embeddings=[embedding.tolist()],
            metadatas=[serialized_meta],
        )
        self.metadata.append({"text": text, **meta})

    def search(self, query: str, k: int = 3, scan_id: str = None):
        self._ensure_init()
        encoder = _get_encoder()

        if encoder is None or self.collection is None:
            return []

        query_embedding = encoder.encode([query])[0].tolist()
        fetch_k = max(k * 10, k) if scan_id else k
        response = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_k,
            include=["documents", "metadatas", "distances"],
        )

        docs = (response.get("documents") or [[]])[0]
        metas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]

        results = []
        for i, doc in enumerate(docs):
            raw_meta = metas[i] if i < len(metas) else {}
            meta = self._deserialize_meta(raw_meta)

            if scan_id and meta.get("scan_id") != scan_id:
                continue

            distance = float(distances[i]) if i < len(distances) else 1.0
            score = 1.0 / (1.0 + max(distance, 0.0))
            results.append(
                {
                    "score": score,
                    "description": doc,
                    "metadata": {"text": doc, **meta},
                }
            )
            if len(results) >= k:
                break

        return results

    def save(self):
        # Chroma PersistentClient commits to disk automatically.
        self._ensure_init()
        return

    def is_ready(self) -> bool:
        self._ensure_init()
        return (_get_encoder() is not None) and (self.collection is not None)

    def reset_database(self):
        """Dangerous: Wipes all data from ChromaDB."""
        self._ensure_init()
        chroma = _get_chroma()
        if chroma is None:
            return

        try:
            client = chroma.PersistentClient(path=self.persist_dir)
            try:
                client.delete_collection(name="spatial_memory")
            except Exception:
                pass # Maybe didn't exist
            
            self.collection = client.get_or_create_collection(name="spatial_memory")
            self.metadata = []
            self._id_counter = 0
            print("✅ Database reset complete.")
        except Exception as e:
            print(f"❌ Database reset failed: {e}")
