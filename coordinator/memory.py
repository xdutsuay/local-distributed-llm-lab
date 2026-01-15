import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Any, Optional

class VectorStore:
    _instance = None
    
    def __new__(cls, persist_directory: str = "data/chroma_db"):
        if cls._instance is None:
            cls._instance = super(VectorStore, cls).__new__(cls)
            cls._instance._init(persist_directory)
        return cls._instance

    def _init(self, persist_directory: str):
        # Ensure data directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="llm_lab_memory",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"🧠 Vector Memory initialized in {persist_directory}")

    def add(self, documents: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, ids: Optional[List[str]] = None) -> None:
        """Add documents to vector store."""
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]
            
        if metadatas is None:
            metadatas = [{"timestamp": "now"} for _ in documents] # Simple default
            
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"🧠 Added {len(documents)} items to memory.")

    def search(self, query: str, n_results: int = 3) -> List[str]:
        """Search for relevant documents."""
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        # Flatten results (results['documents'] is a list of lists)
        return results['documents'][0] if results['documents'] else []

    def count(self) -> int:
        return self.collection.count()

    def clear(self):
        """Dangerous: clears all memory"""
        self.client.delete_collection("llm_lab_memory")
        self.collection = self.client.get_or_create_collection(name="llm_lab_memory")

# Singleton accessor
def get_vector_store():
    return VectorStore()
