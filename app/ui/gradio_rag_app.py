from pathlib import Path

import gradio as gr

from app.services.rag.chunker import build_chunk_metadata, split_text_into_chunks
from app.services.rag.file_reader import read_document
from app.services.rag.rag_service import RagService

# ragservice içinde embeddingservice ve qdrantservice oluşuyor
# gradio tarafında da buradan kullanıcaz
rag_service = RagService()
embedding_service = rag_service.embedding_service
qdrant_service = rag_service.qdrant_service


def normalize_user_id(user_id: str | None) -> str:
    """
    Kullanıcı ID boş gelirse test amaçlı varsayılan bir değer döndürür.
    Gerçek sistemde bu değer giriş yapan kullanıcıdan alınabilir.
    """

    if user_id and user_id.strip():
        return user_id.strip()

    return "test_user_1"


def build_document_id_from_file(file_path: str, document_id: str | None) -> str:
    """
    Doküman ID boş bırakılırsa dosya adından otomatik document_id üretir.
    Böylece aynı kullanıcı aynı dosyayı tekrar yüklediğinde eski kayıtlar silinip yenisi yazılabilir.
    
    """
    if document_id and document_id.strip():
        return document_id.strip()

    file_stem = Path(file_path).stem
    safe_document_id = file_stem.lower().replace(" ", "_")

    return safe_document_id


def format_sources(sources: list[dict]) -> str:
    # ragservice içinden dönen kaynak listesini ekranda okunabilir hale getirir

    if not sources:
        return "kaynak bulunamadı"

    lines = []

    for source in sources:
        score = source.get("score")

        if score is not None:
            score_text = f"{score:.4f}"
        else:
            score_text = "-"

        lines.append(
            f"Kaynak{source.get('source_no')} | "
            f"Dosya: {source.get('file_name')} | "
            f"Chunk: {source.get('chunk_index')} | "
            f"Skor: {score_text}"
        )

    return "\n".join(lines)


def index_document(file_path: str, user_id: str, document_id: str):
    """
    Gradio'dan gelen dosyayı RAG pipeline'a alır.

    Akış:
    1. Gradio dosyayı geçici bir path olarak verir.
    2. read_document bu path üzerinden metni çıkarır.
    3. split_text_into_chunks metni temizleyip chunklara böler.
    4. embedding_service chunklar için embedding üretir.
    5. qdrant_service chunk + embedding + metadata bilgisini Qdrant'a kaydeder.
    """

    if not file_path:
        return (
            "Lütfen önce bir PDF, DOCX veya TXT dosyası yükleyin.",
            user_id,
            document_id,
            ""
        )

    try:
        active_user_id = normalize_user_id(user_id)
        active_document_id = build_document_id_from_file(
            file_path=file_path,
            document_id=document_id
        )

        file_name = Path(file_path).name

        text = read_document(file_path)
        chunks = split_text_into_chunks(text)

        if not chunks:
            return (
                "Dokümandan işlenilebilir metin çıkarılamadı",
                active_user_id,
                active_document_id,
                " "
            )

        metadatas = [
            build_chunk_metadata(
                file_name=file_name,
                chunk_index=index,
                user_id=active_user_id,
                document_id=active_document_id
            )
            for index, _ in enumerate(chunks)
        ]

        embeddings = embedding_service.embed_documents(chunks)

        saved_count = qdrant_service.upsert_document_chunks(
            chunks=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            user_id=active_user_id,
            document_id=active_document_id,
            delete_existing=True
        )

        status_message = (
            "Doküman başarıyla işlendi ve Qdranta kaydediledi \n\n"
            f"Dosya: {file_name}\n"
            f"Kullanıcı ID: {active_user_id}\n"
            f"Doküman ID: {active_document_id}\n"
            f"Chunk sayısı: {len(chunks)}\n"
            f"Kaydedilen chunk sayısı: {saved_count}"
        )

        document_summary = (
            f"İşlenen dosya: {file_name}\n"
            f"Toplam metin uzunluğu : {len(text)} karakter\n"
            f"Chunk sayısı: {len(chunks)}"
        )

        return (
            status_message,
            active_user_id,
            active_document_id,
            document_summary
        )

    except Exception as error:
        return (
            f"Bir hata oluştu: {error}",
            user_id,
            document_id,
            ""
        )


def answer_question(question: str, user_id: str, document_id: str):
    """
    Kullanıcının sorusunu RagService üzerinden cevaplar.

    Akış:
    1. Kullanıcı sorusu alınır.
    2. RagService soruyu embedding'e çevirir.
    3. Qdrant'tan ilgili chunkları getirir.
    4. Chunkları Ollama'ya context olarak gönderir.
    5. Cevap ve kaynak bilgilerini döndürür.
    """
    if not question or not question.strip():
        return "lütfen bir soru yazın ", "kaynak bulunamadı"

    active_user_id = normalize_user_id(user_id)

    if not document_id or not document_id.strip():
        return (
            "lütfen önce bir dokuman yükleyip işletin veya dokuman id girin",
            "kaynak bulunmadı"
        )

    result = rag_service.answer_question(
        question=question.strip(),
        user_id=active_user_id,
        document_id=document_id.strip(),
        top_k=5
    )

    answer = result.get("answer", "cevap üretilemedi")
    sources = format_sources(result.get("sources", []))

    return answer, sources


custom_css = """
.gradio-container {
    max-width: 1180px !important;
    margin: auto !important;
}

#main-title {
    text-align: center;
    padding: 18px 0 6px 0;
}

.panel {
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 18px;
    background: #ffffff;
    box-shadow: 0 8px 24px rgba(0,0,0,0.04);
}

.small-note {
    color: #6b7280;
    font-size: 14px;
}

"""

with gr.Blocks(
    title="HexaOps RAG Doküman Asistanı"
) as demo:

    gr.Markdown(
        """
        # HexaOps RAG Doküman Asistanı
        Doküman yükleyin, sistem metni işleyip Qdrant'a kaydetsin ve ardından dokümana dayalı soru-cevap yapın.
        """,
        elem_id="main-title"
    )

    with gr.Row():
        with gr.Column(scale=1, elem_classes="panel"):
            gr.Markdown("## 1. Doküman Yükleme ve İndeksleme")

            file_input = gr.File(
                label="PDF, DOCX veya TXT dosyası yükleyin",
                file_types=[".pdf", ".docx", ".txt"],
                type="filepath"
            )

            user_id_input = gr.Textbox(
                label="Kullanıcı ID",
                value="test_user_1",
                placeholder="Örn: test_user_1"
            )

            document_id_input = gr.Textbox(
                label="Doküman ID",
                placeholder="Boş bırakırsanız dosya adından otomatik üretilir"
            )

            index_button = gr.Button(
                "Dokümanı İşle ve Kaydet",
                variant="primary"
            )

            index_status = gr.Textbox(
                label="İşlem Durumu",
                lines=7,
                interactive=False
            )

            document_summary = gr.Textbox(
                label="Doküman Özeti",
                lines=4,
                interactive=False
            )

        with gr.Column(scale=1, elem_classes="panel"):
            gr.Markdown("## 2. Dokümana Soru Sor")

            question_input = gr.Textbox(
                label="Soru",
                placeholder="Örn: RAG sistemi dokümanları nasıl işler?",
                lines=3
            )

            answer_button = gr.Button(
                "Cevap Üret",
                variant="primary"
            )

            answer_output = gr.Textbox(
                label="Cevap",
                lines=8,
                interactive=False
            )

            sources_output = gr.Textbox(
                label="Kullanılan Kaynaklar",
                lines=6,
                interactive=False
            )

    gr.Markdown(
        """
        <div class="small-note">
        Not: Bu arayüz ilk RAG prototipi içindir. Aynı kullanıcı ve aynı doküman ID tekrar işlendiğinde eski chunklar silinir ve güncel kayıtlar Qdrant'a yazılır.
        </div>
        """
    )

    index_button.click(
        fn=index_document,
        inputs=[
            file_input,
            user_id_input,
            document_id_input
        ],
        outputs=[
            index_status,
            user_id_input,
            document_id_input,
            document_summary
        ]
    )

    answer_button.click(
        fn=answer_question,
        inputs=[
            question_input,
            user_id_input,
            document_id_input
        ],
        outputs=[
            answer_output,
            sources_output
        ]
    )


if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        server_port=7862,
        css=custom_css
    )