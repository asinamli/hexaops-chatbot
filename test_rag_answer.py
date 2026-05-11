from pathlib import Path

from app.services.rag.chunker import build_chunk_metadata, split_text_into_chunks
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.file_reader import read_document
from app.services.rag.qdrant_service import QdrantService
from app.services.rag.rag_service import RagService


file_path = "docs/rag_test_docs/ornek.txt"

user_id = "test_user_1"
document_id = "rag_answer_test_doc_1"

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

saved_count = qdrant_service.upsert_document_chunks(
    chunks=chunks,
    embeddings=document_embeddings,
    metadatas=metadatas,
    user_id=user_id,
    document_id=document_id,
    delete_existing=True
)

rag_service = RagService()

question = "kahramanmaraş teknokentte hangi firmaların başvurusu açık?"

result = rag_service.answer_question(
    question=question,
    user_id=user_id,
    document_id=document_id,
    top_k=5
)

print("\n--- RAG Cevap Testi ---")
print("Kaydedilen chunk sayısı:", saved_count)
print("Soru:", question)

print("\n--- Cevap ---")
print(result["answer"])

print("\n--- Kullanılan Kaynaklar ---")
for source in result["sources"]:
    print(
        f"Kaynak {source['source_no']} | "
        f"Dosya: {source['file_name']} | "
        f"Chunk: {source['chunk_index']} | "
        f"Skor: {source['score']}"
    )

print("\nRetrieved chunk sayısı:", result["retrieved_count"])