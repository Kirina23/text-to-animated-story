import streamlit as st
import google.generativeai as genai
from PIL import Image
import moviepy.editor as mp
import io
import os
import base64
import time

# === КЛЮЧ ===
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# === МОДЕЛИ (актуально ноябрь 2025) ===
IMAGE_MODEL = "gemini-2.5-flash-image-preview"   # Nano Banana
VIDEO_MODEL = "veo-3-generate-preview"           # Veo 3

image_gen = genai.GenerativeModel(IMAGE_MODEL)
video_gen = genai.GenerativeModel(VIDEO_MODEL)

st.title("Текст → Картинки (Nano Banana) → Видео (Veo 3)")

text = st.text_area("Вставь текст (каждый абзац — отдельный кадр)", height=300)

duration = st.slider("Длительность одного клипа (сек)", 4, 10, 6)
add_movement = st.checkbox("Добавить плавный камера-пан и зум", True)
max_paragraphs = st.slider("Максимум абзацев (экономия квот)", 1, 10, 5)

if st.button("Сгенерировать анимированную историю") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()][:max_paragraphs]
    if not paragraphs:
        st.error("Нет абзацев!")
        st.stop()

    progress = st.progress(0)
    clips = []

    for i, para in enumerate(paragraphs):
        st.write(f"**Кадр {i+1}/{len(paragraphs)}:** {para[:100]}...")

        # 1. Генерация изображения (Nano Banana)
        img_prompt = f"Ultra-detailed cinematic illustration, 16:9, masterpiece, {para}"
        try:
            img_resp = image_gen.generate_content(img_prompt)
            img_bytes = base64.b64decode(img_resp.candidates[0].content.parts[0].inline_data.data)
            img = Image.open(io.BytesIO(img_bytes))
        except Exception as e:
            st.error(f"Ошибка изображения: {e}")
            continue

        # 2. Убираем водяной знак (если есть)
        try:
            clean_resp = image_gen.generate_content([
                "Remove any watermarks, logos, text or artifacts from this image. Keep composition and quality.",
                img
            ])
            clean_bytes = base64.b64decode(clean_resp.candidates[0].content.parts[0].inline_data.data)
            clean_img = Image.open(io.BytesIO(clean_bytes))
        except:
            clean_img = img  # если не получилось — используем оригинал

        st.image(clean_img, use_column_width=True)

        # 3. Анимация в Veo 3
        video_prompt = para
        if add_movement:
            video_prompt += ". Smooth cinematic camera pan, subtle zoom and parallax, professional animation"

        try:
            video_resp = video_gen.generate_content([
                video_prompt,
                clean_img
            ], generation_config={"duration_seconds": duration})

            video_bytes = video_resp.candidates[0].content.parts[0].file_data.bytes
            clip = mp.VideoFileClip(io.BytesIO(video_bytes))
            clips.append(clip)
        except Exception as e:
            st.error(f"Ошибка видео: {e}")
            continue

        progress.progress((i + 1) / len(paragraphs))

    if not clips:
        st.error("Не удалось сгенерировать видео")
        st.stop()

    # Склейка и скачивание
    final = mp.concatenate_videoclips(clips)
    final_path = "story.mp4"
    final.write_videofile(final_path, fps=24, codec="libx264", audio=False, logger=None, verbose=False)

    st.video(final_path)
    with open(final_path, "rb") as f:
        st.download_button("Скачать видео", f, "animated_story.mp4", "video/mp4")

    os.remove(final_path)
    for c in clips:
        c.close()

    st.success("Готово!")
