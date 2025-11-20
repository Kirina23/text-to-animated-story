import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import zipfile
import time

# === ТВОЙ КЛЮЧ ===
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

# АКТУАЛЬНАЯ МОДЕЛЬ (stable, бесплатно, ноябрь 2025)
PROMPT_MODEL = "gemini-2.5-flash"
prompt_model = genai.GenerativeModel(PROMPT_MODEL)

# МОДЕЛЬ Nano Banana для картинок (preview, требует billing для стабильности)
IMAGE_MODEL = "gemini-2.5-flash-image-preview"
image_model = genai.GenerativeModel(IMAGE_MODEL)

st.set_page_config(page_title="Текст → Промпты + Картинки (Nano Banana)", layout="centered")
st.title("📖 Текст → Детальные Промпты + Картинки (Gemini 2.5 Flash + Nano Banana)")

text = st.text_area(
    "Вставь текст (каждый абзац = промпт + картинка)",
    height=300,
    placeholder="Луна светила над старым замком...\n\nВдруг открылась дверь...\n\nИз неё вышел призрак..."
)

style = st.selectbox(
    "Стиль промптов/картинок",
    ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"]
)

generate_images = st.checkbox("Генерировать картинки из промптов (Nano Banana, ~$0.039/шт после free tier)", value=False)

if st.button("🚀 Сгенерировать промпты и картинки", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** промптов и картинок...")

    prompts = []
    images = []
    
    for i, para in enumerate(paragraphs):
        with st.spinner(f"Промпт {i+1}/{len(paragraphs)}"):
            base_prompt = f"Создай детальный промпт для генерации изображения на основе этого абзаца: '{para}'.\n"
            if style != "без стиля":
                base_prompt += f"Стиль: {style}. "
            base_prompt += "Опиши сцену ярко: композиция, освещение, цвета, детали, эмоции. Формат: готовый промпт для AI-генератора (например, 'A highly detailed cinematic scene of...'). Длина: 100–150 слов. На английском для лучшего результата."
            
            try:
                response = prompt_model.generate_content(base_prompt)
                prompt_text = response.text.strip()
                prompts.append(prompt_text)
                st.write(f"**{i+1}. Абзац:** {para[:80]}...")
                st.write(f"**Промпт для картинки:** {prompt_text}")
            except Exception as e:
                st.error(f"Ошибка промпта {i+1}: {e}")
                prompt_text = f"A detailed image of: {para[:100]} in {style} style, masterpiece."
                prompts.append(prompt_text)
                st.write(f"**{i+1}. Абзац:** {para[:80]}...")
                st.write(f"**Промпт (fallback):** {prompt_text}")

            # Генерация картинки из промпта (если включено)
            if generate_images:
                with st.spinner(f"Картинка {i+1}/{len(paragraphs)}"):
                    try:
                        img_response = image_model.generate_content(
                            prompt_text,
                            generation_config=genai.types.GenerationConfig(
                                response_mime_type="image/png",  # Для Nano Banana
                                temperature=0.4  # Стабильность
                            )
                        )
                        # Извлекаем изображение
                        img = img_response.parts[0].inline_data.as_image()  # PIL Image
                        images.append(img)
                        st.image(img, caption=f"Картинка {i+1} (Nano Banana)", use_column_width=True)
                    except Exception as e:
                        st.error(f"Ошибка картинки {i+1}: {e}. Проверь квоты/billing для Nano Banana.")
                        st.info("Совет: Включи billing в https://console.cloud.google.com/billing для стабильной генерации.")

            time.sleep(2)  # Пауза для квот (10 RPM в free tier)

        st.divider()

    if prompts:
        # Все промпты одним файлом
        full_text = "\n\n---\n\n".join([f"Image Prompt {i+1}:\n{prompt}" for i, prompt in enumerate(prompts, 1)])
        st.success("🎉 Готово! Копируй промпты в DALL-E/Midjourney, или используй Nano Banana для картинок.")
        st.download_button(
            "📄 Скачать промпты (TXT)",
            full_text,
            "gemini_image_prompts.txt",
            "text/plain"
        )

    if images:
        # ZIP с картинками
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img in enumerate(images):
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                zf.writestr(f"картинка_{idx+1}.png", buf.getvalue())
        zip_buffer.seek(0)
        st.download_button(
            "📦 Скачать картинки (ZIP)",
            zip_buffer,
            "nano_banana_images.zip",
            "application/zip"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nКвоты: https://ai.dev/usage (free tier: 10 RPM; для Nano Banana — billing для >10 изображений/день).\nВсе картинки с SynthID-водяным знаком.")
