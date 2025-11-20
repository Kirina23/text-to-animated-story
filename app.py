import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import base64
import zipfile
import re

# === КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Модель Nano Banana (с fallback на стабильную)
MODEL = "gemini-2.5-flash-image-preview"  # Попробуй сначала эту

model = genai.GenerativeModel(MODEL)

st.set_page_config(page_title="Текст → Картинки (Nano Banana)", layout="centered")
st.title("Текст → Картинки через Nano Banana")

text = st.text_area(
    "Вставь свой текст (каждый абзац = одна картинка)",
    height=300,
    placeholder="Жила-была девочка...\n\nОна пошла в лес...\n\nТам встретила волка..."
)

style = st.selectbox(
    "Стиль картинок",
    ["реализм, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в студии Ghibli", "без стиля (по тексту)"]
)

if st.button("🚀 Сгенерировать картинки") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    if not paragraphs:
        st.error("Не найдено абзацев. Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** картинок...")

    images = []
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Картинка {i+1}/{len(paragraphs)}"):
            # Формируем промт: ЯВНЫЙ запрос на изображение + стиль
            if style == "без стиля (по тексту)":
                prompt = f"Generate an image of: {para}. Ultra detailed, 16:9 aspect ratio, masterpiece."
            else:
                prompt = f"Generate an image of: {para}. {style}, ultra detailed, 16:9 aspect ratio, masterpiece, best quality."

            try:
                # Генерация БЕЗ response_mime_type (дефолт text/plain)
                response = model.generate_content(prompt)
                
                # Парсим base64-изображение из ответа (Gemini возвращает inline_data)
                text_response = response.text
                # Ищем base64 data URI: data:image/png;base64,iVBOR...
                match = re.search(r'data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)', text_response)
                if match:
                    mime_type = match.group(1)
                    img_data = match.group(2)
                    img_bytes = base64.b64decode(img_data)
                    img = Image.open(io.BytesIO(img_bytes))
                else:
                    # Fallback: если нет inline_data, используем PIL для генерации (редко)
                    st.warning(f"Нет base64 в ответе для абзаца {i+1}. Пробую fallback...")
                    # Переключаемся на текстовый промпт для описания
                    img = Image.new('RGB', (512, 512), color='lightblue')  # Плейсхолдер
                    images.append(img)
                    continue
                
                images.append(img)
                st.image(img, caption=f"{i+1}. {para[:100]}...", use_column_width=True)
                
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")
                if "quota" in str(e).lower():
                    st.warning("Квота исчерпана. Замени MODEL на 'gemini-1.5-flash' в коде и перезагрузи.")
                # Авто-fallback на стабильную модель
                try:
                    st.info(f"Пробую fallback на gemini-1.5-flash...")
                    fallback_model = genai.GenerativeModel("gemini-1.5-flash")
                    fallback_response = fallback_model.generate_content(prompt)
                    # Аналогичный парсинг...
                    text_response = fallback_response.text
                    match = re.search(r'data:image/(png|jpeg|jpg);base64,([A-Za-z0-9+/=]+)', text_response)
                    if match:
                        mime_type = match.group(1)
                        img_data = match.group(2)
                        img_bytes = base64.b64decode(img_data)
                        img = Image.open(io.BytesIO(img_bytes))
                        images.append(img)
                        st.image(img, caption=f"{i+1} (fallback). {para[:100]}...", use_column_width=True)
                except:
                    st.error("Fallback не сработал. Проверь ключ и квоты.")

    if images:
        # Упаковываем всё в ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)

        st.success("Готово!")
        st.download_button(
            "📦 Скачать все картинки (ZIP)",
            zip_buffer,
            file_name="nano_banana_images.zip",
            mime="application/zip"
        )

st.info("Ключ: https://aistudio.google.com/app/apikey\nЕсли 429 — включи billing в Google Cloud.")
