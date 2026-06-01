import gradio as gr
import requests

# FastAPI backendinin URL'i
API_URL = "http://127.0.0.1:8001/api/chat"

# Demo için sabit kullanıcı ve konuşma kimliği
# Bunlar Redis history / follow-up mantığının çalışması için gerekli
DEMO_USER_ID = "demo_user"
DEMO_CONVERSATION_ID = "demo_conversation"


def chat_with_api(message, history):
    if not message or not message.strip():
        return "", history

    try:
        response = requests.post(
            API_URL,
            json={
                "message": message,
                "user_id": DEMO_USER_ID,
                "conversation_id": DEMO_CONVERSATION_ID
            },
            timeout=30
        )
        response.raise_for_status()

        data = response.json()
        answer = data.get("answer", "Cevap alınamadı.")

    except Exception as e:
        answer = f"Hata: {e}"

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer}
    ]

    return "", history


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

    clear_button.click(
        fn=lambda: ("", []),
        inputs=[],
        outputs=[message_box, chatbot]
    )


if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)