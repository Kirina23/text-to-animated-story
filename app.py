import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# МОДЕЛЬ Nano Banana (работает бесплатно!)
MODEL = "gemini-2.5-flash-image"

model = genai.GenerativeModel(MODEL)

st.set_page_config(page_title="Текст → Картинки (Nano Banana)", layout="centered")
st.title("📖 Текст → Картинки (Nano Banana / Gemini)")

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

    st.write(f"Генерирую **{len(paragraphs)}** картинок через Nano Banana...")

    images = []
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Картинка {i+1}/{len(paragraphs)}"):
            prompt = f"Generate an image of: {para}"
            if style != "без стиля":
                prompt += f". {style}, high quality, detailed, 16:9 aspect ratio, masterpiece"

            try:
                # Генерация через generate_content (стандартный метод)
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.4,  # Стабильность
                        response_mime_type="image/png"  # Формат ответа
                    )
                )
                
                # Извлекаем изображение из ответа
                for part in response.parts:
                    if part.inline_data:
                        img = part.inline_data.as_image()  # PIL Image
                        images.append(img)
                        st.image(img, caption=f"{i+1}. {para[:80]}...", use_column_width=True)
                        break
                    else:
                        st.warning(f"Нет изображения в ответе для абзаца {i+1}. Промпт: {prompt[:100]}...")
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")
                if "quota" in str(e).lower():
                    st.warning("Квота исчерпана. Создай новый API-ключ или включи billing в Google Cloud.")

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
            "nano_banana_images.zip",
            "application/zip"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nКвоты: https://ai.dev/usage\nВсе изображения с водяным знаком SynthID.")
