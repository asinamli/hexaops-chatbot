# HexaOps Chatbot

Function calling destekli, FastAPI backend + Gradio arayüz + Ollama tabanlı açık kaynak model kullanan chatbot projesi.

## Proje Özeti

Bu proje, kullanıcı mesajını alıp:
- normal sohbet mesajlarında LLM ile cevap verebilen,
- matematik işlemleri, şirket bilgisi ve hava durumu gibi konularda tool çağırabilen,
- tool sonucunu tekrar LLM'ye verip daha doğal bir cevap üretebilen
bir chatbot altyapısı kurmak amacıyla geliştirilmiştir.

## Kullanılan Teknolojiler

- Python 3.10
- FastAPI
- Uvicorn
- Gradio
- Requests
- Ollama
- Açık kaynak model (örnek: `llama3.2`)

## Klasör Yapısı

```text
hexaops-chatbot/
├─ app/
│  ├─ api/
│  │  ├─ routes/
│  │  │  ├─ chat.py
│  │  │  └─ health.py
│  │  └─ deps.py
│  ├─ core/
│  │  ├─ config.py
│  │  ├─ logging.py
│  │  └─ errors.py
│  ├─ schemas/
│  │  ├─ chat.py
│  │  ├─ llm.py
│  │  └─ tools.py
│  ├─ services/
│  │  ├─ agent_service.py
│  │  ├─ weather_service.py
│  │  └─ company_info_service.py
│  ├─ llm/
│  │  ├─ base.py
│  │  └─ ollama_provider.py
│  ├─ tools/
│  │  ├─ math_tools.py
│  │  ├─ weather_tools.py
│  │  ├─ company_tools.py
│  │  ├─ tool_registry.py
│  │  └─ tool_definitions.py
│  └─ ui/
│     └─ gradio_app.py
├─ docs/
├─ main.py
├─ requirements.txt
├─ .env.example
└─ README.md
```



## Kurulum

### 1. Projeyi aç

PowerShell veya terminalde proje klasörüne gir:

```powershell
cd hexaops-chatbot
```

### 2. Sanal ortam oluştur

```powershell
python -m venv .venv
```

### 3. Sanal ortamı aktif et

```powershell
.venv\Scripts\Activate
```

### 4. Gerekli paketleri yükle

```powershell
pip install -r requirements.txt
```

## Ollama Kurulumu ve Model

### 1. Ollama kurulu olmalı

Bilgisayarda Ollama yüklü ve açık olmalıdır.

### 2. Model indir

Örnek model:

```powershell
ollama pull llama3.2
```

### 3. Modelin indiğini kontrol et

```powershell
ollama list
```

## Yapılandırma

`app/core/config.py` dosyasında Ollama ayarları bulunur:

```python
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
```

Eğer farklı model kullanacaksan burada model adını güncelle.

## Uygulamayı Çalıştırma

Bu projede backend ve arayüz **iki ayrı terminalde** çalıştırılır.

### Terminal 1 – FastAPI backend

```powershell
uvicorn main:app --reload
```

Backend açıldıktan sonra Swagger adresi:

```text
http://127.0.0.1:8000/docs
```

### Terminal 2 – Gradio arayüz

```powershell
python app/ui/gradio_app.py
```

Arayüz adresi:

```text
http://127.0.0.1:7860
```

## Kullanım Örnekleri

### Normal sohbet
- `selam`
- `naber`
- `kendini tanıt`

### Matematik
- `5 + 3`
- `10 - 4`
- `6 * 2`
- `8 / 2`

### Şirket bilgisi
- `mesai saatleriniz`
- `adres nedir`
- `telefon bilgisi`

### Hava durumu
- `ankara hava durumu`
- `osmaniye hava durumu nasıl`
- `istanbul hava durumu`

## Çalışma Mantığı

1. Kullanıcı mesajı önce Gradio arayüzüne gelir.
2. Gradio bu mesajı FastAPI `/api/chat` endpoint'ine gönderir.
3. `agent_service.py` mesajın tool gerektirip gerektirmediğine karar verir.
4. Tool gerekiyorsa LLM tool çağrısı üretir.
5. `tool_registry.py` ilgili Python fonksiyonunu çalıştırır.
6. Tool sonucu tekrar LLM'ye verilir.
7. Nihai cevap kullanıcıya döndürülür.

## Sık Karşılaşılan Sorunlar

### 1. Ollama bağlantı hatası

Eğer model cevap vermiyorsa önce Ollama'nın açık olduğunu kontrol et:

```powershell
ollama list
```

### 2. Model bulunamadı hatası

Model adı yanlış olabilir. `config.py` içindeki model adı ile `ollama list` çıktısı aynı olmalıdır.

### 3. Gradio arayüz açılıyor ama mesaj gitmiyor

Backend terminalinin açık olduğundan emin ol:

```powershell
uvicorn main:app --reload
```

### 4. VS Code `pydantic could not be resolved` uyarısı

Doğru interpreter seçilmemiş olabilir.

VS Code içinde:
- `Ctrl + Shift + P`
- `Python: Select Interpreter`
- `.venv` olan interpreter'ı seç

