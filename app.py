import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# МОДЕЛЬ ДЛЯ ИЗОБРАЖЕНИЙ (Imagen 3 — работает бесплатно!)
MODEL = "imagen-3.0-generate-fast-001"

# Создаём модель для изображений (НЕ GenerativeModel!)
image_model = genai.ImageGenerationModel(MODEL)

st.set_page_config(page_title="Текст → Картинки (Imagen 3)", layout="centered")
st.title("📖 Текст → Картинки (Imagen 3 / Nano Banana)")

text = st.text_area(
    "Вставь текст (каждый абзац = одна картинка)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль картинок",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

if st.button("🚀 Сгенерировать картинки", type="primary") and text.strip():
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
                prompt += f". {style}, высокое качество, детализировано"

            try:
                # Генерация изображений (правильный метод!)
                gen_images = image_model.generate_images(
                    prompt=prompt,
                    number_of_images=1,
                    aspect_ratio="16:9",  # Соотношение сторон
                    safety_filter_level="block_some",  # Фильтр безопасности
                    person_generation="allow_adult"  # Разрешить людей
                )
                img = gen_images.images[0]  # Первое изображение
                images.append(img)
                st.image(img, caption=f"{i+1}. {para[:80]}...", use_column_width=True)
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")
                if "quota" in str(e).lower():
                    st.warning("Квота исчерпана. Создай новый API-ключ или включи billing.")

    if images:
        # ZIP-архив для скачивания
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)

        st.success("🎉 Готово! Картинки сгенерированы.")
        st.download_button(
            "📦 Скачать все картинки (ZIP)",
            zip_buffer,
            "imagen3_story_images.zip",
            "application/zip"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nЕсли ошибки — проверь квоты: https://ai.dev/usage")
