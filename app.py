import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import zipfile
import time

# === КЛИЕНТ С КЛЮЧЕМ ===
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

st.set_page_config(page_title="Текст → Промпты + Картинки (Nano Banana)", layout="centered")
st.title("📖 Текст → Промпты и Картинки (Gemini 2.5 + Nano Banana)")

text = st.text_area(
    "Вставь текст (каждый абзац = промпт + картинка)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

max_paragraphs = st.slider("Макс. абзацев (экономия квот)", 1, 8, 5)

generate_images = st.checkbox("Генерировать реальные картинки (требует billing, ~$0.039/шт)", value=False)

if st.button("🚀 Сгенерировать", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()][:max_paragraphs]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    progress = st.progress(0)
    st.write(f"Обрабатываю **{len(paragraphs)}** абзацев... (с задержкой для квот)")

    prompts = []
    images = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Абзац {i+1}/{len(paragraphs)}"):
            # 1. Генерация промпта (бесплатно, с переводом на EN)
            translate_prompt = f"Translate this Russian paragraph to English: '{para}'."
            try:
                translate_response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=translate_prompt,
                    config=types.GenerateContentConfig(max_output_tokens=150)
                )
                en_para = translate_response.text.strip() if translate_response and translate_response.text and translate_response.text.strip() else para
            except Exception as e:
                st.warning(f"Ошибка перевода {i+1}: {e}. Использую оригинал.")
                en_para = para

            base_prompt = f"Create a detailed image prompt based on this English paragraph: '{en_para}'. Style: {style if style != 'без стиля' else 'natural'}. Format: 'A highly detailed [style] image of [scene], masterpiece, 16:9'. Keep it 100-150 words."
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=base_prompt,
                    config=types.GenerateContentConfig(max_output_tokens=200)
                )
                # Проверка на None/пустой response
                if response and response.text and response.text.strip():
                    img_prompt = response.text.strip()
                else:
                    img_prompt = en_para  # Fallback: английский абзац
                    st.warning(f"Пустой ответ для {i+1}. Использую fallback: {img_prompt[:50]}...")
                prompts.append(img_prompt)
                st.write(f"**{i+1}. Абзац (RU):** {para[:80]}...")
                st.write(f"**Промпт (EN):** {img_prompt}")
            except Exception as e:
                st.error(f"Ошибка промпта {i+1}: {e}")
                img_prompt = en_para
                prompts.append(img_prompt)
                continue

            # 2. Генерация картинки (если включено, Nano Banana без MIME)
            if generate_images:
                try:
                    img_response = client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",  # Nano Banana
                        contents=img_prompt,
                        config=types.GenerateContentConfig(
                            response_modalities=["IMAGE"],  # Только изображение
                            image_config=types.ImageConfig(aspect_ratio="16:9")  # Соотношение сторон
                        )
                    )
                    img_found = False
                    for part in img_response.candidates[0].content.parts:
                        if part.inline_data:
                            img_bytes = part.inline_data.data
                            img = Image.open(io.BytesIO(img_bytes))
                            images.append(img)
                            st.image(img, caption=f"Картинка {i+1}", use_column_width=True)
                            img_found = True
                            break
                    if not img_found:
                        st.warning(f"Нет изображения для {i+1}.")
                except Exception as e:
                    st.error(f"Ошибка картинки {i+1}: {e}. Проверь billing и модель.")

            # Задержка для RPM
            if i < len(paragraphs) - 1:
                time.sleep(6)
        
        progress.progress((i + 1) / len(paragraphs))

    # Скачивания
    if prompts:
        full_prompts = "\n\n---\n\n".join([f"Prompt {i+1}:\n{p}" for i, p in enumerate(prompts, 1)])
        st.download_button(
            "📄 Скачать промпты (TXT)",
            full_prompts,
            "prompts_en.txt",
            "text/plain"
        )

    if images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)
        st.download_button(
            "📦 Скачать картинки (ZIP)",
            zip_buffer,
            "nano_banana_images.zip",
            "application/zip"
        )
        st.success("Готово! (SynthID водяной знак на картинках).")

st.info("🔑 Квоты: https://ai.dev/usage\nДля картинок — billing: https://console.cloud.google.com/billing\nПромпты теперь на английском для лучшего качества.")
