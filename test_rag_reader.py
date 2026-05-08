from app.services.rag.file_reader import read_document
from app.services.rag.chunker import clean_text, split_text_into_chunks


file_path = "docs/rag_test_docs/ornek.txt"

raw_text = read_document(file_path)
cleaned_text = clean_text(raw_text)
chunks = split_text_into_chunks(raw_text)

print("Ham metin uzunluğu:", len(raw_text))
print("Temizlenmiş metin uzunluğu:", len(cleaned_text))
print("Chunk sayısı:", len(chunks))

print("\n--- Temizlenmiş metinden ilk 500 karakter ---")
print(cleaned_text[:500])

for index, chunk in enumerate(chunks, start=1):
    print(f"\n--- Chunk {index} | Uzunluk: {len(chunk)} ---")
    print(chunk[:700])