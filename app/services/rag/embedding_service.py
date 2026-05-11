# CHUNKLARI SAYISAL VEKTÖRE ÇEVİRİR

from sentence_transformers import SentenceTransformer

from app.core.rag_config import RAG_EMBEDDING_MODEL

class EmbeddingService:
    """
     RAG için embedding üretiminden sorumlu servis
     Bu servis:
     doküman chunklarını vektöre çevirir
    """

    def __init__(self, model_name:str = RAG_EMBEDDING_MODEL):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device="cpu")


    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Doküman chunkları için embedding üretir

        if not texts:
            return []
        
        # e5 tabanlı modellerde dokuman metinleri için passage prefixi kullanılır
        prepared_texts = [f"passage: {text}" for text in texts]

        embeddings = self.model.encode(
            prepared_texts,
            normalize_embeddings=True,  # vektörleri normalize ederek benzerlik hesaplamalarında daha iyi sonuç alınır
        )

        return embeddings.tolist()
    
    def embed_query(self, query: str) -> list[float]:
        # Kullanıcı sorgusu için embedding üretir
        # e5 tabanlı modellerde sorgular için query prefixi kullanılır
        prepared_query = f"query: {query}"

        embedding = self.model.encode(
            prepared_query,
            normalize_embeddings=True,
        )

        return embedding.tolist()

