import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector, 
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

    def collection_exists(self) -> bool:
        #qdrant içinde ilgili collection var mı kontrol ediyoruz çünkü aynı kayıtları tkrar tekrar yapmak istemeyiz

        existing_collections = self.client.get_collections().collections
        collection_names = [collection.name for collection in existing_collections]

        return self.collection_name in collection_names

    def ensure_collection(self) -> None:
        # Collection yoksa oluşturur.
        if self.collection_exists():
            return

        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=self.vektor_size, distance=Distance.COSINE),
        )


    def _build_user_document_filter(
            self,
            user_id: str| None = None,
            document_id: str| None = None
    ) -> Filter | None:
        #userid ve documentid değerlerine gre qdrant iltresi üretioruz

        conditions = []

        if user_id:
            conditions.append(
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id)
                )
            )

        if document_id:
            conditions.append(
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            )

        if not conditions:
            return None
        
        return Filter(
            must=conditions
        )
    

    def count_document_chunks(
            self,
            user_id: str,
            document_id: str
    ) -> int:
        # belli bir userid + documaneid değerine ait kaç chunk olduğunu sayar duplice kontrolü için 

        if not self.collection_exists():
            return 0
        
        count_filter = self._build_user_document_filter(
            user_id = user_id,
            document_id= document_id
        )

        result = self.client.count(
            collection_name=self.collection_name,
            count_filter=count_filter,
            exact=True
        )

        return result.count
    
    def delete_document_chunks(
            self,
            user_id: str,
            document_id: str
    ) -> None:
        # aynı userid ve documentid değerine ait etiketleri siler
        #aynı dokuman tekrar yüklendiğinde duplicate kayıt oluşmasını engeller

        if not self.collection_exists():
            return
        delete_filter = self._build_user_document_filter(
            user_id = user_id,
            document_id= document_id
        )
        if delete_filter is None:
            return
        self.client.delete(
            collection_name= self.collection_name,
            points_selector=FilterSelector(
                filter=delete_filter
            ),
            wait=True
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
            points=points,
            wait=True
        )


        return len(points)
    
    def upsert_document_chunks(
            self,
            chunks: list[str],
            embeddings: list[list[float]],
            metadatas: list[dict],
            user_id: str,
            document_id: str,   
            delete_existing: bool = True
    ) -> int:
        # belli bir dokumana ait chunkları kaydedeer
        """
        delete_existing True ise aynı user_id ve document_id değerine sahip mevcut chunkları siler ve yenilerini kaydeder
        daha sonra güncel chunklar tekrar qdranta eklenir 
        """

        if delete_existing:
            self.delete_document_chunks(
                user_id=user_id,
                document_id=document_id
            )

        return self.upsert_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

    def search_similar_chunks(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        user_id: str | None = None,
        document_id: str | None = None
    ) -> list[dict]:
        """
        Kullanıcı sorusuna en yakın chunkları getirir
        user_id verilirse yalnızca o kullanıcıya ait chunklar filtrelenir
        """

        query_filter = self._build_user_document_filter(
            user_id=user_id,
            document_id=document_id
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

        