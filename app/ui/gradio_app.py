import gradio as gr
import requests

# FastAPI backendinin URL'i
API_URL = "http://127.0.0.1:8000/api/chat"


# mesaj alıyor apiye gönderiyor cevabı alıyor ve sohbet ekranına ekliyor
def chat_with_api(message, history):
    if not message or not message.strip():
        return "", history

    try:
        response = requests.post(
            API_URL,
            json={"message": message},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        answer = data.get("answer", "cevap alınamadı")

    except Exception as e:
        answer = f"Hata: {e}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer}
    ]

    return "", history


# Gradio arayüzünün genel yapısını kuruyoruz
with gr.Blocks(title="HexaOps Sohbet Botu") as demo:
    gr.Markdown(
        """
        # HexaOps Sohbet Botu

        Fonksiyon çağırma destekli chatbot arayüzü
        """
    )

    chatbot = gr.Chatbot(
        label="Sohbet",
        height=430
    )

    message_box = gr.Textbox(
        label="Mesajlarınız",
        placeholder="Mesajınızı buraya yazın ve Enter'a basın",
        lines=1
    )

    with gr.Row():
        send_button = gr.Button("Gönder")
        clear_button = gr.Button("Temizle")

    # mesajı göndermeleri için buton ve enter tuşu faaliyeti
    send_button.click(
        fn=chat_with_api,
        inputs=[message_box, chatbot],
        outputs=[message_box, chatbot]
    )

    message_box.submit(
        fn=chat_with_api,
        inputs=[message_box, chatbot],
        outputs=[message_box, chatbot]
    )

    # temizleme butonu faaliyeti
    clear_button.click(
        fn=lambda: ("", []),
        inputs=[],
        outputs=[message_box, chatbot]
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)