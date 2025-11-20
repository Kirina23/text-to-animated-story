import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import base64
import zipfile

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# ЭТО РАБОЧАЯ БЕСПЛАТНАЯ МОДЕЛЬ ДЛЯ КАРТИНОК (Imagen 3 fast)
MODEL = "imagen-3.0-generate-fast-001"   # ← именно эта работает бесплатно!

model = genai.GenerativeModel(MODEL)

st.set_page_config(page_title="Текст → Картинки (Imagen 3)", layout="centered")
st.title("Текст → Картинки (Imagen 3 / Nano Banana бесплатно)")

text = st.text_area(
    "Вставь текст (каждый абзац = одна картинка)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

if st.button("Сгенерировать картинки", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** картинок через Imagen 3...")

    images = []
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Картинка {i+1}/{len(paragraphs)}"):
            prompt = para
            if style != "без стиля":
                prompt += f". {style}, высокое качество, 16:9"

            try:
                # Генерация изображения (Imagen 3)
                img = model.generate_images(prompt, number_of_images=1)[0]
                images.append(img)
                st.image(img, caption=f"{i+1}. {para[:80]}...", use_column_width=True)
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")

    if images:
        # ZIP-архив для скачивания
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)

        st.success("Готово! Картинки сгенерированы")
        st.download_button(
            "Скачать все картинки (ZIP)",
            zip_buffer,
            "imagen3_story_images.zip",
            "application/zip"
        )
