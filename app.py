import streamlit as st
import google.generativeai as genai
import requests
import time
from PIL import Image
import io
import zipfile

# === Gemini для промптов ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# === fal.ai — бесплатный Flux (не требует ключа!) ===
FLUX_URL = "https://fal.run/fal-ai/flux/schnell"

st.set_page_config(page_title="Текст → Промпты + Картинки (Flux)", layout="centered")
st.title("Текст → Промпты + Реальные Картинки (Flux schnell)")

text = st.text_area("Вставь текст (каждый абзац = одна картинка)", height=300)
style = st.selectbox("Стиль", ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"])

if st.button("Сгенерировать промпты и картинки", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    st.write(f"Обрабатываю {len(paragraphs)} абзацев...")

    images = []
    prompts = []

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Абзац {i+1}/{len(paragraphs)}"):
            # 1. Генерируем отличный EN-промпт через Gemini (как у тебя было)
            base = f"Создай детальный промпт для генерации изображения на основе абзаца: '{para}'.\n"
            if style != "без стиля":
                base += f"Стиль: {style}. "
            base += "Яркое описание сцены, композиция, свет, цвета, детали. 100–150 слов. Только на английском."
            
            response = model.generate_content(base)
            prompt_en = response.text.strip()
            prompts.append(prompt_en)

            st.write(f"**{i+1}.** {para[:100]}...")
            st.code(prompt_en, language="text")

            # 2. Генерируем картинку через Flux (бесплатно!)
            try:
                payload = {
                    "prompt": prompt_en,
                    "image_size": "landscape_16_9"   # или "square", "portrait_4_3" и т.д.
                }
                r = requests.post(FLUX_URL, json=payload, timeout=60)
                r.raise_for_status()
                img = Image.open(io.BytesIO(r.content))
                images.append(img)
                st.image(img, caption=f"Картинка {i+1} — Flux schnell", use_column_width=True)
            except Exception as e:
                st.error(f"Ошибка генерации картинки {i+1}: {e}")

            time.sleep(1.5)  # чтобы не спамить

        st.divider()

    # Скачивание ZIP с картинками
    if images:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)
        st.download_button(
            "Скачать все картинки (ZIP)",
            zip_buffer,
            "flux_images.zip",
            "application/zip"
        )

    st.success("Готово! Всё сгенерировано прямо в приложении — бесплатно и без billing.")
