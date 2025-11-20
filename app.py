import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import io
import zipfile
import time
import random  # Для jitter в retry

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

def generate_with_retry(model_name, contents, config, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_name, contents=contents, config=config)
            return response
        except Exception as e:
            if '503' in str(e) or 'UNAVAILABLE' in str(e):
                wait = (2 ** attempt) + random.uniform(0, 1)  # Exponential backoff + jitter
                st.warning(f"Перегрузка сервера (503). Повтор {attempt+1}/{max_retries} через {wait:.1f} сек...")
                time.sleep(wait)
            else:
                raise e
    return None  # Если все ретраи провалились

if st.button("🚀 Сгенерировать", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()][:max_paragraphs]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    progress = st.progress(0)
    st.write(f"Обрабатываю **{len(paragraphs)}** абзацев... (с retry для 503)")

    prompts = []
    images = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Абзац {i+1}/{len(paragraphs)}"):
            # 1. Перевод на EN (если RU)
            translate_prompt = f"Translate this paragraph to English accurately: '{para}'."
            translate_response = generate_with_retry("gemini-2.5-flash", translate_prompt, types.GenerateContentConfig(max_output_tokens=150))
            en_para = translate_response.text.strip() if translate_response and translate_response.text and translate_response.text.strip() else para

            # 2. Генерация промпта на EN
            base_prompt = f"Create a detailed image prompt based on this English paragraph: '{en_para}'. Style: {style if style != 'без стиля' else 'natural'}. Format: 'A highly detailed [style] image of [scene], masterpiece, 16:9'. Keep it 100-150 words."
            response = generate_with_retry("gemini-2.5-flash", base_prompt, types.GenerateContentConfig(max_output_tokens=200))
            if response and response.text and response.text.strip():
                img_prompt = response.text.strip()
            else:
                img_prompt = f"A detailed image of: {en_para[:200]}..."  # Улучшенный fallback на EN
                st.warning(f"Пустой ответ для {i+1}. Fallback EN-промпт.")
            prompts.append(img_prompt)
            st.write(f"**{i+1}. Абзац (RU):** {para[:80]}...")
            st.write(f"**Промпт (EN):** {img_prompt}")
            st.divider()

            # 3. Картинки (если включено)
            if generate_images:
                img_response = generate_with_retry("gemini-2.5-flash-image-preview", img_prompt, types.GenerateContentConfig(max_output_tokens=1290))  # Без MIME, токены для image
                img_found = False
                if img_response:
                    for part in img_response.candidates[0].content.parts:
                        if part.inline_data:
                            img_bytes = part.inline_data.data
                            img = Image.open(io.BytesIO(img_bytes))
                            images.append(img)
                            st.image(img, caption=f"Картинка {i+1}", use_column_width=True)
                            img_found = True
                            break
                if not img_found:
                    st.warning(f"Нет изображения для {i+1}. (Проверь billing — free tier = 0 для image).")

            # Задержка для RPM (10/мин)
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

st.info("🔑 Квоты: https://ai.dev/usage (free: 10 RPM, 250 RPD для промптов; 0 для image).\nBilling для картинок: https://console.cloud.google.com/billing (Tier 1: 500 RPM, $0.039/изобр.).\nПромпты теперь всегда на EN.")
