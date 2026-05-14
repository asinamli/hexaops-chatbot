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


# LLM E gönderilicek toplam context uzunluğu 
#token limitini aşmamak için ilk başta karakter bazlı basit bir sınır kullanıyoruz 
RAG_MAX_CONTEXT_CHARS = 4000

# çok düşük skorlu retrieval sonuçlarında cevap üretmeyi engellemek için başlangıç eşiği 
# nihai tesgtlere göre güncellencek
RAG_MIN_SCORE = 0.50

# RAG cevap üretiminde kullanılacak LLM modeli
# Normal chatbot modelinden bağımsız test edebilmek için ayrı tutuldu.
RAG_LLM_MODEL = "gemma3:4b"
