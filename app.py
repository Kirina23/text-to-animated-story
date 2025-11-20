import streamlit as st
import google.generativeai as genai
import requests
from PIL import Image
import io
import zipfile
import time

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

generate_images = st.checkbox("Генерировать картинки из промптов (Pollinations.AI, бесплатно, без billing)", value=False)

if st.button("🚀 Сгенерировать промпты", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    if not paragraphs:
        st.error("Нет абзацев! Разделяй их пустой строкой.")
        st.stop()

    st.write(f"Генерирую **{len(paragraphs)}** детальных промптов для изображений...")

    prompts = []
    images = []
    
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
            except Exception as e:
                st.error(f"Ошибка на абзаце {i+1}: {e}")

            # Генерация картинки из промпта (если включено, через Pollinations.AI — бесплатно, без ключа)
            if generate_images:
                with st.spinner(f"Картинка {i+1}/{len(paragraphs)}"):
                    success = False
                    for attempt in range(3):  # Retry 3 раза для timeout
                        try:
                            # Pollinations.AI API (бесплатно, без ключа, по docs GitHub)
                            url = "https://image.pollinations.ai/prompt/" + prompt_text.replace(" ", "%20")
                            r = requests.get(url, timeout=120)  # Увеличил до 120 сек (по рекомендациям GitHub)
                            r.raise_for_status()
                            img = Image.open(io.BytesIO(r.content))
                            images.append(img)
                            st.image(img, caption=f"Картинка {i+1} (Pollinations.AI)", use_column_width=True)
                            success = True
                            break
                        except Exception as e:
                            if "timed out" in str(e).lower():
                                st.warning(f"Timeout (перегрузка сервера). Retry {attempt+1}/3 через 10 сек...")
                                time.sleep(10)
                            else:
                                st.error(f"Ошибка картинки {i+1}: {e}. API может быть перегружен (попробуй позже).")
                                break
                    if not success:
                        st.warning(f"Не удалось сгенерировать картинку {i+1} после 3 попыток. Сервер Pollinations перегружен — попробуй позже.")

            time.sleep(2)  # Пауза для квот Gemini (10 RPM в free tier)

        st.divider()

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
            "pollinations_images.zip",
            "application/zip"
        )

st.info("🔑 Ключ: https://aistudio.google.com/app/apikey\nКвоты: https://ai.dev/usage (промпты бесплатно; картинки — Pollinations.AI, без лимитов, без billing).\nВсе картинки генерируются внутри приложения.")
