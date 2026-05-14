# HexaOps RAG Pipeline Prototipi

Bu doküman, HexaOps chatbot projesi içinde geliştirilen RAG tabanlı doküman işleme ve soru-cevap prototipini açıklamak için hazırlanmıştır.

RAG modülü, mevcut chatbot mimarisinden bağımsız olarak geliştirilmiş ayrı bir prototip akıştır. Amaç; kullanıcının yüklediği dokümanları işlemek, bu dokümanları vektör veritabanına kaydetmek ve daha sonra kullanıcının sorularına yüklenen dokümanlara dayalı cevap üretmektir.

---

## 1. Amaç

Bu RAG prototipinin temel amacı, chatbot sistemine özel dokümanlardan bilgi getirme yeteneği kazandırmaktır.

Bu yapı sayesinde sistem:

- PDF, DOCX ve TXT dosyalarını okuyabilir.
- Doküman metnini temizleyip parçalara ayırabilir.
- Her metin parçası için embedding üretebilir.
- Chunkları metadata bilgileriyle birlikte Qdrant vektör veritabanına kaydedebilir.
- Kullanıcının sorusuna göre ilgili doküman parçalarını bulabilir.
- Bulunan parçaları LLM’e context olarak vererek dokümana dayalı cevap üretebilir.
- Cevapla birlikte kullanılan kaynakları gösterebilir.

---

## 2. Mevcut Durum

RAG prototipi şu anda geliştirme aşamasındadır.

Tamamlanan temel özellikler:

- Doküman okuma yapısı
- Metin temizleme
- Chunking işlemi
- Embedding üretimi
- Qdrant’a kayıt
- Qdrant üzerinden similarity search
- `user_id` ve `document_id` ile filtreleme
- Aynı doküman tekrar yüklendiğinde duplicate kayıtların önlenmesi
- RagService ile kaynaklı cevap üretimi
- Gradio üzerinden doküman yükleme ve soru-cevap arayüzü
- Kaynakta bulunmayan bilgiler için no-answer kontrolü
- RAG tarafında ayrı LLM modeli kullanımı

Devam eden iyileştirme başlıkları:

- Cevap kalitesinin artırılması
- No-answer kararının daha kontrollü hale getirilmesi
- Retrieval sonuçlarının daha iyi değerlendirilmesi
- Gerekirse reranking veya hybrid search eklenmesi
- Mevcut tool-calling chatbot mimarisiyle ileride birleştirme

---

## 3. Kullanılan Teknolojiler

| Bileşen | Kullanılan Teknoloji |
|---|---|
| Arayüz | Gradio |
| Backend dili | Python |
| Doküman okuma | PDF / DOCX / TXT reader yapısı |
| Chunking | Custom chunking pipeline |
| Embedding modeli | `intfloat/multilingual-e5-base` |
| Vektör veritabanı | Qdrant |
| LLM | Ollama üzerinden local model |
| RAG cevap üretimi | Custom `RagService` |
| Veri izolasyonu | `user_id` + `document_id` metadata filtreleme |

---

## 4. Genel Mimari Akış

RAG pipeline temel olarak iki ana akıştan oluşur.

### 4.1 Doküman Yükleme ve İndeksleme Akışı

```text
Kullanıcı doküman yükler
        ↓
Gradio dosya path bilgisini alır
        ↓
file_reader.py dokümandan metin çıkarır
        ↓
chunker.py metni temizler ve chunklara böler
        ↓
embedding_service.py chunk embeddinglerini üretir
        ↓
qdrant_service.py chunk + embedding + metadata bilgisini Qdrant’a kaydeder
```

### 4.2 Soru-Cevap Akışı

```text
Kullanıcı soru sorar
        ↓
RagService soruyu embedding’e çevirir
        ↓
Qdrant üzerinden ilgili chunklar aranır
        ↓
İlgili chunklar context haline getirilir
        ↓
Context + kullanıcı sorusu Ollama’ya gönderilir
        ↓
LLM dokümana dayalı cevap üretir
        ↓
Cevap ve kullanılan kaynaklar kullanıcıya gösterilir
```

---

## 5. RAG Dosya Yapısı

RAG modülü ana olarak aşağıdaki dosyalar üzerinden ilerlemektedir.

```text
app/
  core/
    rag_config.py

  services/
    rag/
      file_reader.py
      chunker.py
      embedding_service.py
      qdrant_service.py
      rag_service.py

  ui/
    gradio_rag_app.py

docs/
  rag/
    README.md
```

### Dosya Açıklamaları

| Dosya | Görevi |
|---|---|
| `rag_config.py` | RAG tarafındaki chunk, embedding, Qdrant ve LLM ayarlarını tutar. |
| `file_reader.py` | PDF, DOCX ve TXT dosyalarından metin çıkarır. |
| `chunker.py` | Metni temizler, chunklara ayırır ve chunk metadata bilgilerini oluşturur. |
| `embedding_service.py` | Doküman chunkları ve kullanıcı soruları için embedding üretir. |
| `qdrant_service.py` | Qdrant collection oluşturma, kayıt, silme ve similarity search işlemlerini yönetir. |
| `rag_service.py` | Retrieval, prompt oluşturma, Ollama’ya gönderme ve kaynaklı cevap üretme akışını yönetir. |
| `gradio_rag_app.py` | Doküman yükleme ve dokümana dayalı soru-cevap için Gradio arayüzünü sağlar. |

---

## 6. RAG Ayarları

RAG tarafındaki temel ayarlar `app/core/rag_config.py` içinde tutulur.

Örnek ayarlar:

```python
RAG_CHUNK_SIZE = 800
RAG_CHUNK_OVERLAP = 150
RAG_TOP_K = 5

RAG_EMBEDDING_MODEL = "intfloat/multilingual-e5-base"
RAG_LLM_MODEL = "gemma3:4b"

QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION_NAME = "rag_chunks"

RAG_MAX_CONTEXT_CHARS = 4000
RAG_MIN_SCORE = 0.50
```

Bu değerler ilk prototip için belirlenmiştir. Nihai değerler retrieval kalitesi, cevap doğruluğu ve cevap süresi testlerine göre güncellenebilir.

---

## 7. Qdrant Çalıştırma

RAG pipeline’ın çalışabilmesi için Qdrant servisinin açık olması gerekir.

Docker ile Qdrant çalıştırmak için:

```powershell
docker run -d --name hexaops-qdrant -p 6333:6333 -p 6334:6334 -v hexaops_qdrant_data:/qdrant/storage qdrant/qdrant
```

Çalışan containerları kontrol etmek için:

```powershell
docker ps
```

Qdrant daha önce oluşturulduysa tekrar oluşturmak yerine mevcut container başlatılabilir:

```powershell
docker start hexaops-qdrant
```

---

## 8. Ollama Modeli

RAG cevap üretimi için Ollama üzerinden local LLM kullanılmaktadır.

RAG tarafında kullanılan model `rag_config.py` içinde ayrı tutulur:

```python
RAG_LLM_MODEL = "gemma3:4b"
```

Bu tercih, normal chatbot modelinden bağımsız olarak RAG cevap kalitesini test edebilmek için yapılmıştır.

Ollama’da modelleri kontrol etmek için:

```powershell
ollama list
```

Gerekirse model indirmek için:

```powershell
ollama pull gemma3:4b
```

---

## 9. Gradio RAG Arayüzünü Çalıştırma

Proje kök dizininde sanal ortam aktifken aşağıdaki komut çalıştırılır:

```powershell
python -m app.ui.gradio_rag_app
```

Varsayılan arayüz adresi:

```text
http://127.0.0.1:7862
```

Arayüz iki ana bölümden oluşur:

1. Doküman yükleme ve indeksleme
2. Dokümana soru sorma

---

## 10. Gradio Kullanım Akışı

### 10.1 Doküman Yükleme

Arayüzde önce PDF, DOCX veya TXT dosyası seçilir.

Sonra:

```text
Dokümanı İşle ve Kaydet
```

butonuna basılır.

Bu işlem sonrasında sistem:

- Dokümanı okur.
- Metni çıkarır.
- Metni chunklara ayırır.
- Embedding üretir.
- Chunkları Qdrant’a kaydeder.
- Doküman özeti ve chunk sayısını ekranda gösterir.

### 10.2 Dokümana Soru Sorma

Doküman işlendikten sonra kullanıcı soru alanına sorusunu yazar.

Örnek soru:

```text
Çok worker ortamında history neden dağılabilir?
```

Sistem ilgili chunkları Qdrant’tan getirir ve LLM üzerinden dokümana dayalı cevap üretir.

---

## 11. Metadata Yapısı

Her chunk Qdrant’a kaydedilirken metadata ile birlikte saklanır.

Örnek metadata:

```python
{
    "file_name": "ornek_dokuman.docx",
    "chunk_index": 0,
    "user_id": "test_user_1",
    "document_id": "ornek_dokuman"
}
```

Bu yapı sayesinde:

- Hangi chunk’ın hangi dosyadan geldiği bilinir.
- Kullanıcı bazlı veri izolasyonu sağlanır.
- Aynı doküman tekrar yüklendiğinde eski chunklar silinip güncel chunklar kaydedilebilir.
- Cevapla birlikte kaynak bilgisi gösterilebilir.

---

## 12. Duplicate Kayıt Önleme

Aynı `user_id` ve `document_id` ile doküman tekrar yüklendiğinde eski chunklar önce silinir, ardından yeni chunklar kaydedilir.

Bu sayede:

- Qdrant içinde aynı dokümandan kopya chunklar birikmez.
- Retrieval sonuçları eski ve yeni kayıtlarla karışmaz.
- Gradio üzerinden aynı dosya tekrar işlense bile veritabanı şişmez.

---

## 13. Kullanıcı ve Doküman İzolasyonu

RAG tarafında `user_id` ve `document_id` alanları filtreleme için kullanılır.

Amaç:

```text
Bir kullanıcının yüklediği dokümanın başka bir kullanıcının sorgusunda görünmemesi.
```

Mevcut prototipte kullanıcı ID manuel girilmektedir. Gerçek ürün entegrasyonunda bu bilgi auth/session sisteminden alınabilir.

---

## 14. Test Edilen Akışlar

Şu ana kadar test edilen temel akışlar:

- TXT dosyasından metin okuma
- Uzun metni chunklara ayırma
- Chunk sayısı kontrolü
- Embedding boyutu kontrolü
- Qdrant’a kayıt
- Qdrant similarity search
- Duplicate kayıt önleme
- `user_id` filtresi
- `document_id` filtresi
- Dokümana dayalı cevap üretimi
- Kaynak gösterimi
- Gradio üzerinden doküman yükleme ve soru-cevap

---

## 15. Bilinen Geliştirme Noktaları

Mevcut prototip çalışır durumda olsa da aşağıdaki alanlarda iyileştirme devam etmektedir:

- LLM cevaplarının daha doğru ve doğal hale getirilmesi
- Kaynakta bilgi olduğu halde no-answer cevabı verilmesinin azaltılması
- Retrieval sonuçlarının debug edilmesi
- Gerekirse `top_k`, `chunk_size`, `chunk_overlap` değerlerinin yeniden test edilmesi
- Daha güçlü LLM modellerinin karşılaştırılması
- Türkçe dokümanlar için farklı embedding modellerinin test edilmesi
- Reranking eklenmesi
- Hybrid search yaklaşımının değerlendirilmesi
- Ana chatbot mimarisi ile RAG akışının router/orchestrator üzerinden birleştirilmesi

---

## 16. Mevcut Chatbot ile İlişkisi

Bu RAG prototipi, mevcut tool-calling chatbot mimarisiyle aynı proje içinde yer almaktadır; ancak şu anda ayrı bir geliştirme akışı olarak ilerlemektedir.

Mevcut chatbot tarafında:

- Normal sohbet
- Tool-calling
- Weather/math/company gibi araçlar
- History ve rate limit yapıları

bulunmaktadır.

RAG tarafında ise:

- Doküman yükleme
- Doküman işleme
- Vektör veritabanına kayıt
- Dokümana dayalı cevap üretimi

yer almaktadır.

İlerleyen aşamada bu iki yapı merkezi bir router/orchestrator katmanı üzerinden birleştirilebilir. Böylece sistem, kullanıcının mesajına göre normal sohbet, tool-calling veya RAG akışına yönlenebilir.

---

## 17. Sonraki Adımlar

Planlanan sonraki teknik adımlar:

1. Cevap kalitesi ve no-answer davranışının iyileştirilmesi
2. Retrieval sonuçlarını daha görünür hale getirecek debug çıktılarının eklenmesi
3. Farklı LLM modellerinin karşılaştırılması
4. Türkçe ve çok dilli embedding modellerinin test edilmesi
5. Reranking veya hybrid search araştırması
6. Gradio arayüzünün daha düzenli demo ekranı haline getirilmesi
7. Ana chatbot mimarisi ile RAG akışının nasıl birleşeceğinin planlanması

---

## 18. Kısa Özet

Bu RAG prototipi, HexaOps chatbot sistemine doküman tabanlı bilgi getirme ve kaynaklı cevap üretme yeteneği kazandırmak için geliştirilmiştir.

Mevcut durumda doküman yükleme, metin çıkarma, chunking, embedding üretimi, Qdrant kayıt/retrieval ve Gradio üzerinden soru-cevap akışı çalışmaktadır. Cevap kalitesi, model seçimi ve retrieval iyileştirmeleri üzerinde geliştirme devam etmektedir.