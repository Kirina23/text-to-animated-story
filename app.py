import streamlit as st
from google import genai  # Новый SDK для Gemini 2.5+
from google.genai import types  # Для config
from PIL import Image
import io
import zipfile

# === КЛИЕНТ С КЛЮЧЕМ (явно, чтобы избежать ValueError) ===
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)  # Теперь работает!

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

generate_images = st.checkbox("Генерировать реальные картинки (требует billing, ~$0.039/шт)", value=False)

if st.button("🚀 Сгенерировать", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Обрабатываю **{len(paragraphs)}** абзацев...")

    prompts = []
    images = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Абзац {i+1}/{len(paragraphs)}"):
            # 1. Генерация промпта (бесплатно, через gemini-2.5-flash)
            base_prompt = f"Создай детальный промпт для изображения на основе: '{para}'. Стиль: {style if style != 'без стиля' else 'натуральный'}. Формат: 'A highly detailed [style] image of [scene], masterpiece, 16:9'."
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=base_prompt,
                    config=types.GenerateContentConfig(max_output_tokens=200)
                )
                img_prompt = response.text.strip()
                prompts.append(img_prompt)
                st.write(f"**{i+1}. Абзац:** {para[:80]}...")
                st.write(f"**Промпт:** {img_prompt}")
            except Exception as e:
                st.error(f"Ошибка промпта {i+1}: {e}")
                continue

            # 2. Генерация картинки (если включено, через Nano Banana)
            if generate_images:
                try:
                    # Nano Banana: промпт для изображения
                    img_response = client.models.generate_content(
                        model="gemini-2.5-flash-image-preview",  # Nano Banana
                        contents=img_prompt,
                        config=types.GenerateContentConfig(response_mime_type="image/png")
                    )
                    # Извлекаем изображение из parts (по docs)
                    img_found = False
                    for part in img_response.candidates[0].content.parts:
                        if part.inline_data:
                            img_bytes = part.inline_data.data  # base64 bytes
                            img = Image.open(io.BytesIO(img_bytes))
                            images.append(img)
                            st.image(img, caption=f"Картинка {i+1}", use_column_width=True)
                            img_found = True
                            break
                    if not img_found:
                        st.warning(f"Нет изображения для абзаца {i+1}. Проверь промпт.")
                except Exception as e:
                    st.error(f"Ошибка картинки {i+1}: {e}. Проверь billing и квоты (нужен Tier 1).")

    # Скачивания
    if prompts:
        full_prompts = "\n\n---\n\n".join([f"Prompt {i+1}:\n{p}" for i, p in enumerate(prompts, 1)])
        st.download_button(
            "📄 Скачать промпты (TXT)",
            full_prompts,
            "prompts.txt",
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
        st.success("Готово! Картинки сгенерированы (с SynthID водяным знаком).")

st.info("🔑 Billing для картинок: https://console.cloud.google.com/billing\nКвоты: https://ai.dev/usage\nБез чекбокса — только промпты бесплатно.")
