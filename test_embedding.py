from app.services.rag.file_reader import read_document
from app.services.rag.chunker import split_text_into_chunks
from app.services.rag.embedding_service import EmbeddingService


file_path = "docs/rag_test_docs/ornek.txt"

text = read_document(file_path)
chunks = split_text_into_chunks(text)

embedding_service = EmbeddingService()

document_embeddings = embedding_service.embed_documents(chunks)
query_embedding = embedding_service.embed_query("RAG sistemi dokümanları nasıl işler?")

print("Chunk sayısı:", len(chunks))
print("Doküman embedding sayısı:", len(document_embeddings))

if document_embeddings:
    print("İlk doküman embedding boyutu:", len(document_embeddings[0]))

print("Soru embedding boyutu:", len(query_embedding))
print("Soru embedding ilk 5 değer:", query_embedding[:5])