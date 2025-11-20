import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import zipfile
import time
import random

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

def generate_with_retry(model_name, contents, config=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_name, contents=contents, config=config)
            return response
        except Exception as e:
            error_str = str(e)
            if '503' in error_str or 'UNAVAILABLE' in error_str:
                wait = (2 ** attempt) + random.uniform(0, 1)
                st.warning(f"Перегрузка (503). Повтор {attempt+1}/{max_retries} через {wait:.1f} сек...")
                time.sleep(wait)
            elif '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                st.error(f"Квота исчерпана (429) для {model_name}. Включи billing: https://console.cloud.google.com/billing")
                return None
            else:
                raise e
    return None

if st.button("🚀 Сгенерировать", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()][:max_paragraphs]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    progress = st.progress(0)
    st.write(f"Обрабатываю **{len(paragraphs)}** абзацев... (retry для 503)")

    prompts = []
    images = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Абзац {i+1}/{len(paragraphs)}"):
            # 1. Перевод на EN (с retry)
            translate_prompt = f"Translate this paragraph to English accurately, keeping key visual details: '{para}'."
            translate_response = generate_with_retry("gemini-2.5-flash", [translate_prompt], types.GenerateContentConfig(max_output_tokens=150))
            en_para = translate_response.text.strip() if translate_response and translate_response.text and translate_response.text.strip() else para

            # 2. Генерация промпта на EN (без лишнего нарратива)
            base_prompt = f"Extract the core visual scene from this English paragraph: '{en_para}'. Ignore narrative, introduction, history, questions, or 'what do they have in common'. Describe only the main visual elements (objects, setting, action, lighting, colors, composition). Style: {style if style != 'без стиля' else 'natural'}. Format: 'A highly detailed [style] image of [visual scene description], masterpiece, 16:9'. Keep it 60-100 words, vivid and focused."
            response = generate_with_retry("gemini-2.5-flash", [base_prompt], types.GenerateContentConfig(max_output_tokens=200))
            if response and response.text and response.text.strip():
                img_prompt = response.text.strip()
            else:
                # Улучшенный fallback: Короткий EN-промпт без лишнего (ручная экстракция)
                key_words = en_para.split(',')[0] if ',' in en_para else en_para.split('.')[0]  # Первое ключевое предложение
                img_prompt = f"A highly detailed {style} image of the main visual scene involving {key_words}, masterpiece, 16:9."
                st.warning(f"Пустой ответ для {i+1}. Fallback EN-промпт без нарратива.")
            prompts.append(img_prompt)
            st.write(f"**{i+1}. Абзац (RU):** {para[:80]}...")
            st.write(f"**Промпт (EN):** {img_prompt}")
            st.divider()

            # 3. Картинки (если включено, по docs)
            if generate_images:
                img_response = generate_with_retry("gemini-2.5-flash-image", [img_prompt])  # Без config, по docs
                img_found = False
                if img_response:
                    for part in img_response.parts:
                        if part.inline_data is not None:
                            img = part.as_image()  # part.as_image() по docs
                            images.append(img)
                            st.image(img, caption=f"Картинка {i+1}", use_column_width=True)
                            img_found = True
                            break
                if not img_found:
                    st.warning(f"Нет изображения для {i+1}. Billing обязателен для Nano Banana (free tier = 0).")

            # Задержка для RPM
            if i < len(paragraphs) - 1:
                time.sleep(6)
        
        progress.progress((i + 1) / len(paragraphs))

    # Скачивания
    if prompts:
        full_prompts = "\n\n---\n\n".join([f"Prompt {i+1}:\n{p}" for i, p in enumerate(prompts, 1)])
        st.download_button("📄 Скачать промпты (EN, TXT)", full_prompts, "prompts_en.txt", "text/plain")

    if images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)
        st.download_button("📦 Скачать картинки (ZIP)", zip_buffer, "nano_banana_images.zip", "application/zip")
        st.success("Готово! (SynthID на картинках).")

st.info("🔑 Квоты: https://ai.dev/usage (free: 10 RPM для промптов; 0 для image).\nBilling для картинок: https://console.cloud.google.com/billing ($0.039/изобр.).\nПромпты теперь на EN, без лишнего (только визуал).")
