import streamlit as st
import google.generativeai as genai
import time

genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")

st.set_page_config(page_title="Текст → Промпты (Gemini 2.5)", layout="centered")
st.title("Текст → Идеальные промпты для картинок (Gemini 2.5 Flash)")

text = st.text_area("Вставь текст (каждый абзац = одна сцена)", height=300)
style = st.selectbox("Стиль", ["реалистично, кинематографично", "аниме", "акварель", "фэнтези", "киберпанк", "как в Pixar", "без стиля"])

if st.button("Сгенерировать промпты", type="primary") and text.strip():
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    st.write(f"Генерирую **{len(paragraphs)}** промптов...")

    for i, para in enumerate(paragraphs):
        with st.spinner(f"Промпт {i+1}/{len(paragraphs)}"):
            base = f"Создай детальный промпт для генерации изображения на основе абзаца: '{para}'.\n"
            if style != "без стиля": base += f"Стиль: {style}. "
            base += "Яркое описание сцены, композиция, свет, цвета, детали. 100–150 слов. Только на английском."
            
            response = model.generate_content(base)
            prompt = response.text.strip()

            st.write(f"**{i+1}.** {para[:100]}...")
            st.code(prompt, language="text")

            # Кнопки для мгновенной генерации
            col1, col2, col3 = st.columns(3)
            with col1:
                leo = f"https://app.leonardo.ai/image-generation?prompt={prompt.replace(' ', '%20')}"
                st.markdown(f"[Leonardo.AI]({leo})", unsafe_allow_html=True)
            with col2:
                flux = f"https://flux.ai/image?prompt={prompt.replace(' ', '%20')}"
                st.markdown(f"[Flux]({flux})", unsafe_allow_html=True)
            with col3:
                mj = f"https://www.midjourney.com/app/?prompt={prompt.replace(' ', '%20')}"
                st.markdown(f"[Midjourney]({mj})", unsafe_allow_html=True)

            st.divider()
            time.sleep(1.5)

    st.success("Готово! Кликай по ссылки — картинки генерируются мгновенно и бесплатно.")
