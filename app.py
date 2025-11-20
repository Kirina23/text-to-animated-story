import streamlit as st
import google.generativeai as genai
from PIL import Image
import moviepy.editor as mp
import io
import time
import os

# Настройка API (в Streamlit Cloud добавишь в Secrets)
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# Модели (актуальные на ноябрь 2025)
IMAGE_MODEL = "gemini-2.5-flash-image-preview"  # это и есть Nano Banana
VIDEO_MODEL = "veo-3.0-generate-preview"       # Veo 3 в Gemini API

image_gen = genai.GenerativeModel(IMAGE_MODEL)
video_gen = genai.GenerativeModel(VIDEO_MODEL)

st.title("📖 Текст → Картинки (Nano Banana) → Анимация (Veo 3)")

text = st.text_area("Вставь текст (абзацы разделяй пустой строкой)", height=300)

duration_per_clip = st.slider("Длительность одного клипа (сек)", 4, 10, 6)
add_movement = st.checkbox("Добавить плавный camera pan/zoom в каждый клип", value=True)

if st.button("🚀 Сгенерировать историю") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    
    if not paragraphs:
        st.error("Нет абзацев")
        st.stop()
    
    progress = st.progress(0)
    status = st.empty()
    
    images = []      # очищенные изображения
    video_clips = [] # клипы для склейки
    
    for i, para in enumerate(paragraphs):
        status.text(f"Обрабатываю абзац {i+1}/{len(paragraphs)}: генерирую изображение...")
        
        # Хороший промпт для Nano Banana (кинематографично, детально)
        prompt = f"Highly detailed cinematic illustration, masterpiece, best quality, {para: {para}"
        
        # Генерация изображения
        img_response = image_gen.generate_content(prompt)
        img = img_response.image  # PIL Image с водяным знаком
        
        # Удаление водяного знака через editing (самый чистый способ 2025 года)
        status.text(f"Убираю водяной знак с кадра {i+1}...")
        clean_img = image_gen.generate_content([
            img,
            "Remove any watermarks, logos, text overlays, signatures from the image. Keep exact composition and quality."
        ]).image
        
        images.append(clean_img)
        
        # Показываем картинку сразу
        st.image(clean_img, caption=f"Кадр {i+1}: {para[:80]}...", use_column_width=True)
        
        # Анимация через Veo 3 (image-to-video)
        status.text(f"Анимирую кадр {i+1} в Veo 3...")
        
        video_prompt = para
        if add_movement:
            video_prompt += ". Smooth cinematic camera pan and subtle parallax movement, professional animation, 8k"
        
        video_response = video_gen.generate_content([
            video_prompt,
            clean_img  # start frame
        ],
        generation_config={
            "duration_seconds": duration_per_clip,
            "aspect_ratio": "16:9"
        })
        
        # Veo возвращает видео в bytes
        video_bytes = video_response.video.bytes  # или video_response.candidates[0].content.parts[0].file_data.file_uri — зависит от версии SDK
        # Если возвращает URI в Cloud Storage — скачиваем, но в большинстве случаев даёт bytes напрямую
        
        clip = mp.VideoFileClip(io.BytesIO(video_bytes))
        video_clips.append(clip)
        
        progress.progress((i + 1) / len(paragraphs))
    
    # Склейка всех клипов в одно видео
    status.text("Склеиваю финальное видео...")
    final_video = mp.concatenate_videoclips(video_clips, method="compose")
    
    # Сохраняем временно
    final_path = "final_story.mp4"
    final_video.write_videofile(final_path, fps=24, codec="libx264", audio=False)
    
    # Показываем результат
    st.success("Готово!")
    st.video(final_path)
    
    # Кнопка скачивания
    with open(final_path, "rb") as file:
        st.download_button(
            label="Скачать финальное видео",
            data=file,
            file_name="my_animated_story.mp4",
            mime="video/mp4"
        )
    
    # Очистка
    os.remove(final_path)
    for clip in video_clips:
        clip.close()
