# DOKÜMANDAN METİN ÇIKARIR

from pathlib import Path

import fitz  # PyMuPDF
from docx import Document

def read_txt(file_path: str) -> str:
    #txt dosyasından metin okur 

    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()
    

def read_pdf(file_path: str) -> str:
    """
    pdf dosyasından sayfa sayfa metin çıkarır 
    ilk aşamada metni düz alıyorum 
    ilerleyen aşamalarda sayfa numarası, başlık gibi bilgileri de ekleyebilirim
    """

    text_parts = []

    pdf_document = fitz.open(file_path)

    for page_index, page in enumerate(pdf_document):
        page_text = page.get_text()
        
        if page_text and page_text.strip():  # Boş olmayan sayfaları ekle
            text_parts.append(page_text.strip())

    pdf_document.close()

    return "\n".join(text_parts)


def read_docx(file_path: str) -> str:
    """
    docx dosyasından paragrafları okuyarak metin oluşturur
    """

    document = Document(file_path)
    paragraphs = []
    
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:  # Boş olmayan paragrafları ekle
            paragraphs.append(text)

    return "\n".join(paragraphs)


def read_document(file_path: str) -> str:
    """
    Dosya türüne göre uygun okuma fonksiyonunu çağırır
    """

    path = Path(file_path)
    extension = path.suffix.lower()

    if extension == ".txt":
        return read_txt(file_path)
    elif extension == ".pdf":
        return read_pdf(file_path)
    elif extension == ".docx":
        return read_docx(file_path)
    
    raise ValueError(f"Unsupported file type: {extension}")