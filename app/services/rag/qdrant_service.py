import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.rag_config import QDRANT_COLLECTION_NAME, QDRANT_URL  

class QdrantService:
    """
    rag için qdrant vektör veritabanı işlemlerinden sorumlu servis 
    bu servis:
    collection oluşturur
    chunk embeddinglerini metadata ile kaydeder
    kullanıcı sorusuna göre benzer chunk araması yapar 
    """

    def __init__(
        self,
        collection_name: str = QDRANT_COLLECTION_NAME,
        url: str = QDRANT_URL,
        vektor_size: int = 768,  # embedding boyutu, kullandığınız modele göre değişebilir

    ):
        self.collection_name = collection_name
        self.client = QdrantClient(url=url)
        self.vektor_size = vektor_size

    def ensure_collection(self) -> None:
        # Collection yoksa oluşturur.

        existing_collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in existing_collections]

        if self.collection_name in collection_names:
            return
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vektor_size, distance=Distance.COSINE),
        )

    def upsert_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict]
    ) -> int:
    
        #Chunk embedding ve metadata bilgilerini Qdranta kaydeder
        

        if not chunks:
            return 0

        if len(chunks) != len(embeddings) or len(chunks) != len(metadatas):
            raise ValueError("chunks, embeddings ve metadatas aynı uzunlukta olmalıdır.")

        self.ensure_collection()

        points = []

        for chunk, embedding, metadata in zip(chunks, embeddings, metadatas):
            point_id = str(uuid.uuid4())

            payload = {
                "text": chunk,
                **metadata
            }

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return len(points)

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: str | None = None
    ) -> list[dict]:
        """
        Kullanıcı sorusuna en yakın chunkları getirir
        user_id verilirse yalnızca o kullanıcıya ait chunklar filtrelenir
        """

        query_filter = None

        if user_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="user_id",
                        match=MatchValue(value=user_id)
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=query_filter
        )

        matches = []

        for point in results.points:
            matches.append(
                {
                    "score": point.score,
                    "text": point.payload.get("text"),
                    "metadata": {
                        key: value
                        for key, value in point.payload.items()
                        if key != "text"
                    }
                }
            )

        return matches