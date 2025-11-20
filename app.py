import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import base64
import zipfile

# === Твой API-ключ (добавишь в Secrets) ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Модель Nano Banana (она же gemini-2.5-flash-image-preview или стабильная 1.5-flash)
# Если будет 429 — просто поменяй на "gemini-1.5-flash" (бесплатно и без лимитов)
MODEL = "gemini-2.5-flash-image-preview"   # ← попробуй сначала эту
# MODEL = "gemini-1.5-flash"              # ← запасной вариант (100% бесплатно)

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
            # Формируем промт
            if style == "без стиля (по тексту)":
                prompt = para
            else:
                prompt = f"{para}. {style}, ультра детализация, 16:9, шедевр"

            try:
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "image/png"}
                )
                img_data = response.candidates[0].content.parts[0].inline_data.data
                img_bytes = base64.b64decode(img_data)
                img = Image.open(io.BytesIO(img_bytes))
                
                images.append(img)
                st.image(img, caption=f"{i+1}. {para[:100]}...", use_column_width=True)
                
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")
                if "quota" in str(e).lower():
                    st.warning("Квота исчерпана. Попробуй модель gemini-1.5-flash (замени строку 12 в коде)")

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

st.info("Ключ получи тут → https://aistudio.google.com/app/apikey\nЗатем добавь в Secrets на Streamlit Cloud")
