import streamlit as st
from pypdf import PdfReader
import random
import io

# --- Функции ---

def parse_questions_from_text(text):
    """Разбирает текст на вопросы и варианты ответов, включая правильные."""
    text_no_pages = "\n".join([line for line in text.split('\n') if "--- PAGE" not in line])
    question_blocks = text_no_pages.strip().split('?')
    parsed_questions = []
    for block in question_blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines: continue
        first_option_index = -1
        for i, line in enumerate(lines):
            if line.startswith('+') or line.startswith('-'):
                first_option_index = i
                break
        if first_option_index == -1: continue
        question_text = " ".join(lines[:first_option_index])
        options = []
        correct_answer = ""
        current_option_parts = []
        is_correct_buffer = False
        for line in lines[first_option_index:]:
            is_new_option_line = line.startswith('+') or line.startswith('-')
            if is_new_option_line and current_option_parts:
                full_option_text = " ".join(current_option_parts)
                options.append(full_option_text)
                if is_correct_buffer: correct_answer = full_option_text
                current_option_parts = []
            if is_new_option_line:
                is_correct_buffer = line.startswith('+')
            current_option_parts.append(line.lstrip('+- ').strip())
        if current_option_parts:
            full_option_text = " ".join(current_option_parts)
            options.append(full_option_text)
            if is_correct_buffer: correct_answer = full_option_text
        if question_text and options and correct_answer:
            parsed_questions.append({"question": question_text, "options": options, "correct_answer": correct_answer})
    return parsed_questions

def extract_text_from_pdf_pypdf(pdf_stream):
    """Извлекает текст из PDF с помощью pypdf."""
    try:
        reader = PdfReader(pdf_stream)
        full_text = "".join(page.extract_text() + "\n" for page in reader.pages)
        return full_text
    except Exception as e:
        st.error(f"Ошибка при чтении PDF: {e}")
        return None

# --- Инициализация состояния сессии (упрощенная) ---
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.questions = []
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.user_answer = ""
    st.session_state.current_options = []

# --- Основной интерфейс приложения ---
st.set_page_config(layout="centered")
st.title("🎓 Интерактивный тест по PDF")

# Если тест еще не начат, показываем экран загрузки и настроек
if not st.session_state.quiz_started:
    st.write("Загрузите PDF-файл и настройте тест.")
    uploaded_file = st.file_uploader("Выберите PDF файл", type="pdf", label_visibility="collapsed")
    
    if uploaded_file:
        with st.spinner('Пожалуйста, подождите. Идет обработка вашего PDF-файла...'):
            pdf_stream = io.BytesIO(uploaded_file.read())
            text = extract_text_from_pdf_pypdf(pdf_stream)
        
        if text:
            all_questions = parse_questions_from_text(text)
            if all_questions:
                st.success(f"Файл успешно обработан! Найдено вопросов: {len(all_questions)}")
                st.divider()
                
                num_questions_slider = st.slider(
                    "Выберите количество вопросов в тесте:", 
                    min_value=5, 
                    max_value=len(all_questions), 
                    value=min(40, len(all_questions)), 
                    step=5
                )
                
                if st.button("Начать тест!", type="primary"):
                    st.session_state.questions = random.sample(all_questions, num_questions_slider)
                    st.session_state.quiz_started = True
                    # Готовим первый вопрос
                    first_question_options = st.session_state.questions[0]['options'][:]
                    random.shuffle(first_question_options)
                    st.session_state.current_options = first_question_options
                    st.rerun()
            else:
                st.warning("В файле не найдены вопросы в ожидаемом формате.")

# Если тест начался, показываем вопросы или результаты
else:
    # Если еще есть вопросы
    if st.session_state.current_question_index < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.current_question_index]
        total_questions = len(st.session_state.questions)
        
        progress_value = (st.session_state.current_question_index) / total_questions
        st.progress(progress_value, text=f"Вопрос {st.session_state.current_question_index + 1}/{total_questions}")
        st.info(f"Текущий счет: {st.session_state.score}")
        st.subheader(q["question"])
        
        if not st.session_state.answer_submitted:
            st.session_state.user_answer = st.radio("Выберите ответ:", st.session_state.current_options, key=f"q_{st.session_state.current_question_index}")
            if st.button("Ответить"):
                st.session_state.answer_submitted = True
                if st.session_state.user_answer == q["correct_answer"]:
                    st.session_state.score += 1
                st.rerun()
        else:
            if st.session_state.user_answer == q["correct_answer"]:
                st.success(f"Правильно! Ваш ответ: {st.session_state.user_answer}")
            else:
                st.error(f"Неправильно. Ваш ответ: {st.session_state.user_answer}")
                st.info(f"Верный ответ: {q['correct_answer']}")
            
            if st.button("Следующий вопрос"):
                st.session_state.current_question_index += 1
                st.session_state.answer_submitted = False
                if st.session_state.current_question_index < total_questions:
                    next_q = st.session_state.questions[st.session_state.current_question_index]
                    next_options = next_q['options'][:]
                    random.shuffle(next_options)
                    st.session_state.current_options = next_options
                st.rerun()
    # Если вопросы закончились
    else:
        st.header("Тест завершен!")
        total = len(st.session_state.questions)
        score = st.session_state.score
        percentage = round((score / total) * 100) if total > 0 else 0
        
        st.success(f"Ваш результат: {score} из {total} ({percentage}%)")
        
        if percentage >= 90: st.balloons()
        
        if st.button("Пройти тест еще раз"):
            # Сбрасываем состояние для нового теста
            st.session_state.quiz_started = False
            st.session_state.questions = []
            st.session_state.current_question_index = 0
            st.session_state.score = 0
            st.session_state.answer_submitted = False
            st.session_state.current_options = []
            st.rerun()
