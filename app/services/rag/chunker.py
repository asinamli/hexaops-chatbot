# METNİ TEMİZLER VE CHUNKLARA BÖLER

import re

from app.core.rag_config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE


def clean_text(text: str) -> str:
    
    #Metni temizler, gereksiz boşlukları kaldırır
    """
    gereksiz boş satırları silmek
    tab ve fazla boşlukları sadeleşrtirmek
    pdflerde görülebilen satır sonu bölünmelerini azaltmak
    türkçe karakterleri bozmadan metni düzeltmek
    """
    

    if not text:
        return ""
    
    # bazı dosyalarda görülebilen görünmeyen karakterleri temizliyoruz
    text = text.replace("\ufeff", "")
    text = text.replace("\x00", "")
    text = text.replace("\u00a0", " ")
    text = text.replace("\t", " ")

    # pdflerde bazen kelime satır sonunda tire ile bölünebiliyor 
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # satırlrı tek tek temizlipruz
    lines = text.splitlines()
    cleaned_lines = []


    for line in lines:
        line = line.strip()  # satır başı ve sonu boşlukları temizle

        # satır içindeki fazla boşlukları tek boşluğa indir
        line = re.sub(r"\s+", " ", line)

        if line:  # boş olmayan satırları ekle
            cleaned_lines.append(line)

    # parağrafları tek satır manığında birleştirelim
    cleaned_text = "\n".join(cleaned_lines)

    #çok fazla boşluk kaldıysa tekrar sadeleştir
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)

    return cleaned_text.strip()


def find_best_split_point(text:str, start: int, end: int) -> int:
    """
    Metni bölmek için en uygun noktayı bulur
    Öncelikle cümle sonu noktalama işaretlerine bakar
    Eğer yoksa kelime sınırına bakar
    Hiçbir uygun nokta bulunamazsa verilen end indeksini döner
    """

    if end >= len(text):
        return len(text)

    search_area = text[start:end]

    # Önce sn satır sonunu bul 
    newline_index = search_area.rfind("\n")
    if newline_index != -1 and newline_index> len(search_area) * 0.5:  # bölme noktasının metnin ortasına yakın olmasını sağla
        return start + newline_index
    
    # olmazsa son boşluğu bul 
    space_index = search_area.rfind(" ")
    if space_index != -1 and space_index > len(search_area) * 0.5:  # bölme noktasının metnin ortasına yakın olmasını sağla
        return start + space_index
    

    # hiç uygun nokta bulunamazsa verilen end indeksini döner
    return end


def adjust_start_to_word_boundary(text: str, start: int) -> int:
    """
    Overlap nedeniyle chunk başlangıcı kelimenin ortasına denk gelirse
    başlangıcı en yakın kelime sınırına çeker.
    """

    if start <= 0:
        return 0

    if start >= len(text):
        return len(text)

    while start < len(text) and text[start].isspace():
        start += 1

    if start <= 0 or start >= len(text):
        return start

    if text[start - 1].isalnum() and text[start].isalnum():
        search_start = max(0, start - 80)

        previous_space = text.rfind(" ", search_start, start)
        previous_newline = text.rfind("\n", search_start, start)

        boundary = max(previous_space, previous_newline)

        if boundary != -1:
            start = boundary + 1

    while start < len(text) and text[start].isspace():
        start += 1

    return start


def split_text_into_chunks(
        text: str,
        chunk_size: int = RAG_CHUNK_SIZE,
        chunk_overlap: int = RAG_CHUNK_OVERLAP
) -> list[str]:
    """
    Metni belirli boyutlarda parçalara böler
    Parçaların birbirini belirli bir oranda örtmesini sağlar
    Bölme noktalarını cümle sonu veya kelime sınırlarına göre optimize eder
    """

    if not text or not text.strip():
        return []
    
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap, chunk_size değerinden küçük olmalıdır.")
    

    text = clean_text(text)
    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:
        target_end = start + chunk_size
        end = find_best_split_point(text, start, target_end)

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        next_start = max(end - chunk_overlap, 0)
        start = adjust_start_to_word_boundary(text, next_start)

    return chunks


def build_chunk_metadata(
    file_name: str,
    chunk_index: int,
    user_id: str | None = None,
    document_id: str | None = None  
) -> dict:
    """
    Her bir chunk için metadata oluşturur
    Metadata, chunkun hangi dosyadan geldiği, sırası ve isteğe bağlı olarak kullanıcı ve belge bilgilerini içerir
    """
    return {
        "file_name": file_name,
        "chunk_index": chunk_index,
        "user_id": user_id,
        "document_id": document_id
    }