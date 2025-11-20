import streamlit as st
import google.generativeai as genai

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# АКТУАЛЬНАЯ МОДЕЛЬ (stable, бесплатно, ноябрь 2025)
MODEL = "gemini-2.5-flash"

model = genai.GenerativeModel(MODEL)

st.set_page_config(page_title="Текст → Описания Картинок (Gemini 2.5)", layout="centered")
st.title("📖 Текст → Детальные Промпты для Картинок (Gemini 2.5 Flash)")

text = st.text_area(
    "Вставь текст (каждый абзац = промпт для одной картинки)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль промптов",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

if st.button("🚀 Сгенерировать промпты", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** детальных промптов для изображений...")

    prompts = []
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Промпт {i+1}/{len(paragraphs)}"):
            base_prompt = f"Создай детальный промпт для генерации изображения на основе этого абзаца: '{para}'.\n"
            if style != "без стиля":
                base_prompt += f"Стиль: {style}. "
            base_prompt += "Опиши сцену ярко: композиция, освещение, цвета, детали, эмоции. Формат: готовый промпт для AI-генератора (например, 'A highly detailed cinematic scene of...'). Длина: 100–150 слов. На английском для лучшего результата."

            try:
                response = model.generate_content(base_prompt)
                prompt_text = response.text.strip()
                prompts.append(prompt_text)
                st.write(f"**{i+1}. Абзац:** {para[:80]}...")
                st.write(f"**Промпт для картинки:** {prompt_text}")
                st.divider()
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")

    if prompts:
        # Все промпты одним файлом для скачивания
        full_text = "\n\n---\n\n".join([f"Image Prompt {i+1}:\n{prompt}" for i, prompt in enumerate(prompts, 1)])
        
        st.success("🎉 Готово! Копируй промпты в DALL-E, Midjourney или Imagen для генерации реальных картинок.")
        st.download_button(
            "📄 Скачать все промпты (TXT)",
            full_text,
            "gemini_image_prompts.txt",
            "text/plain"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nКвоты: https://ai.dev/usage\nМодель gemini-2.5-flash — бесплатно, без лимитов на старте. Для реальных изображений включи billing и используй gemini-2.5-flash-image.")
