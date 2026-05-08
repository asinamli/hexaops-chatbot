from pathlib import Path

from app.services.rag.file_reader import read_document
from app.services.rag.chunker import build_chunk_metadata, split_text_into_chunks
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.qdrant_service import QdrantService


file_path = "docs/rag_test_docs/ornek.txt"
user_id = "test_user_1"
document_id = "test_doc_1"

file_name = Path(file_path).name

text = read_document(file_path)
chunks = split_text_into_chunks(text)

metadatas = [
    build_chunk_metadata(
        file_name=file_name,
        chunk_index=index,
        user_id=user_id,
        document_id=document_id
    )
    for index, _ in enumerate(chunks)
]

embedding_service = EmbeddingService()
document_embeddings = embedding_service.embed_documents(chunks)

qdrant_service = QdrantService()

saved_count = qdrant_service.upsert_chunks(
    chunks=chunks,
    embeddings=document_embeddings,
    metadatas=metadatas
)

query = "RAG sisteminde dokümanlar nasıl işlenir?"
query_embedding = embedding_service.embed_query(query)

results = qdrant_service.search_similar_chunks(
    query_embedding=query_embedding,
    top_k=3,
    user_id=user_id
)

print("Kaydedilen chunk sayısı:", saved_count)
print("Soru:", query)
print("Bulunan sonuç sayısı:", len(results))

for index, result in enumerate(results, start=1):
    print(f"\n--- Sonuç {index} ---")
    print("Skor:", result["score"])
    print("Metadata:", result["metadata"])
    print("Metin:", result["text"][:500])