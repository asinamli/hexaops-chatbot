# RAG tarafında kullanılacak temel ayarlar

# İlk testlerde bu değerleri deneme başlangıcı olarak kullanacağız.
# Nihai değerler retrieval kalitesi ve cevap süresine göre belirlenecek.
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 150

# Kullanıcı sorusuna en yakın kaç chunk getirilecek?
RAG_TOP_K = 5

# İlk embedding modeli.
# Çok dilli destek sunduğu için başlangıç adayı olarak seçildi.
RAG_EMBEDDING_MODEL = "intfloat/multilingual-e5-base"

# Qdrant ayarları
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION_NAME = "rag_chunks"