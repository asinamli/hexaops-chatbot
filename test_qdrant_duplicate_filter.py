"""
Bu test dosyası iki kritik RAG davranışını kontrol eder:

1. Duplicate kayıt kontrolü:
   Aynı user_id + document_id tekrar işlendiğinde eski chunklar silinir,
   yeni chunklar tekrar kaydedilir ve Qdrant içinde aynı dokümandan kopya kayıt birikmez.

2. Kullanıcı bazlı veri izolasyonu:
   test_user_1 kendi dokümanından sonuç alabilir.
   test_user_2 aynı document_id ile arama yapsa bile test_user_1'in dokümanını göremez.

Bu yapı ileride gerçek kullanıcı dokümanlarında önemlidir;
çünkü bir kullanıcının yüklediği belge başka bir kullanıcının arama sonucunda görünmemelidir.
"""

from pathlib import Path

from app.services.rag.file_reader import read_document
from app.services.rag.chunker import build_chunk_metadata, split_text_into_chunks
from app.services.rag.embedding_service import EmbeddingService
from app.services.rag.qdrant_service import QdrantService

file_path = "docs/rag_test_docs/ornek.txt"  

user_id_1 = "test_user_1"
user_id_2 = "test_user_2"
document_id = "duplicate_test_doc_1"

file_name = Path(file_path).name

text = read_document(file_path)
chunks = split_text_into_chunks(text)

metadatas = [
    build_chunk_metadata(
        file_name=file_name,
        chunk_index=index,
        user_id=user_id_1,
        document_id=document_id
    )
    for index, _ in enumerate(chunks)

]

embedding_service = EmbeddingService()
document_embeddings = embedding_service.embed_documents(chunks)

qdrant_service = QdrantService()
print("başlangıç chunk sayısı: ", len(chunks))

saved_count_1 = qdrant_service.upsert_document_chunks(
    chunks=chunks,
    embeddings=document_embeddings,
    metadatas=metadatas,
    user_id=user_id_1,
    document_id=document_id,
    delete_existing=True
)

count_after_first_upload = qdrant_service.count_document_chunks(
    user_id=user_id_1,
    document_id=document_id     


)

saved_count_2 = qdrant_service.upsert_document_chunks(
    chunks=chunks,
    embeddings=document_embeddings,
    metadatas=metadatas,
    user_id=user_id_1,
    document_id=document_id,
    delete_existing=True
)

count_after_second_upload = qdrant_service.count_document_chunks(
    user_id=user_id_1,
    document_id=document_id     
)

query = "RAG sisteminde dokümanlar nasıl işlenir"
query_embedding = embedding_service.embed_query(query)

user_1_results = qdrant_service.search_similar_chunks(
    query_embedding=query_embedding,
    top_k=3,
    user_id=user_id_1,
    document_id=document_id
)

user_2_results = qdrant_service.search_similar_chunks(
    query_embedding=query_embedding,
    top_k=3,
    user_id=user_id_2,
    document_id=document_id
)

print( "--- Test Sonuçları ---")
print("İlk yüklemede kaydedilen chunk sayısı:", saved_count_1)
print("İlk yüklemeden sonra qdranttaki chunk sayısı:", count_after_first_upload)
print("İkinci yüklemede kaydedilen chunk sayısı:", saved_count_2)
print("İkinci yüklemeden sonra qdranttaki chunk sayısı:", count_after_second_upload)

print("user_id filtre testi")
print("User 1 sonuç sayısı:", len(user_1_results))
print("User 2 sonuç sayısı:", len(user_2_results))

for index, result in enumerate(user_1_results, start=1):
    print(f"\n --- user_1 sonuç {index} --- ")
    print("Skor:", result["score"])
    print("Metadata:", result["metadata"])
    print("Metin:", result["text"][:500])