import streamlit as st
import google.generativeai as genai

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# Стабильная модель для описаний (бесплатно, без preview-лимитов)
MODEL = "gemini-1.5-flash"

model = genai.GenerativeModel(MODEL)

st.set_page_config(page_title="Текст → Описания Картинок (Gemini)", layout="centered")
st.title("📖 Текст → Детальные Описания для Картинок (Gemini)")

text = st.text_area(
    "Вставь текст (каждый абзац = описание одной картинки)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль описаний",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

if st.button("🚀 Сгенерировать описания", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** детальных описаний для картинок...")

    descriptions = []
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Описание {i+1}/{len(paragraphs)}"):
            prompt = f"Создай детальное описание для генерации изображения на основе этого абзаца текста: '{para}'.\n"
            if style != "без стиля":
                prompt += f"Стиль: {style}. "
            prompt += "Опиши сцену ярко, с деталями освещения, цветов, композиции, в формате промпта для AI-генератора изображений (например, 'Highly detailed cinematic scene of...'). Длина: 100–200 слов."

            try:
                response = model.generate_content(prompt)
                desc = response.text.strip()
                descriptions.append(desc)
                st.write(f"**{i+1}. Абзац:** {para[:80]}...")
                st.write(f"**Описание для картинки:** {desc}")
                st.divider()
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")

    if descriptions:
        # Текст для скачивания (все описания одним файлом)
        full_text = "\n\n---\n\n".join([f"Картинка {i+1}:\n{desc}" for i, desc in enumerate(descriptions, 1)])
        
        st.success("🎉 Готово! Используй эти описания в Midjourney, DALL-E или AI Studio для генерации реальных картинок.")
        st.download_button(
            "📄 Скачать все описания (TXT)",
            full_text,
            "gemini_image_prompts.txt",
            "text/plain"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nЭто бесплатно и без лимитов. Для реальных картинок — включи billing и используй Imagen в Vertex AI.")
