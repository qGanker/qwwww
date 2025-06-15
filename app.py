import streamlit as st
from pypdf import PdfReader
import random
import io
import pandas as pd
import os
import time

# --- Константы и функции ---

LEADERBOARD_FILE = "leaderboard.csv"

def initialize_leaderboard():
    """Создает CSV-файл для таблицы лидеров, если он не существует."""
    if not os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "w", newline="", encoding='utf-8') as f:
            f.write("Ник,Группа,Процент,Правильных,Всего\n")

def save_score(nickname, group, score, total):
    """Сохраняет результат пользователя в CSV-файл."""
    percentage = round((score / total) * 100) if total > 0 else 0
    with open(LEADERBOARD_FILE, "a", newline="", encoding='utf-8') as f:
        f.write(f'"{nickname}","{group}",{percentage},{score},{total}\n')

def load_leaderboard(search_query=""):
    """Загружает и отображает таблицу лидеров с возможностью поиска."""
    if os.path.exists(LEADERBOARD_FILE) and os.path.getsize(LEADERBOARD_FILE) > 20:
        try:
            df = pd.read_csv(LEADERBOARD_FILE)
            if search_query:
                df = df[df['Ник'].str.contains(search_query, case=False, na=False)]
            df_sorted = df.sort_values(by="Процент", ascending=False).reset_index(drop=True)
            st.subheader("🏆 Таблица лидеров (Топ-10)")
            st.dataframe(df_sorted.head(10))
        except Exception:
            st.info("Таблица лидеров пока пуста.")
    else:
        st.info("Таблица лидеров пока пуста. Пройдите тест, чтобы стать первым!")

def parse_questions_from_text(text):
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
    try:
        reader = PdfReader(pdf_stream)
        full_text = "".join(page.extract_text() + "\n" for page in reader.pages)
        return full_text
    except Exception as e:
        st.error(f"Ошибка при чтении PDF: {e}")
        return None

# --- Инициализация состояния сессии (добавлены новые поля) ---
if 'page' not in st.session_state:
    st.session_state.page = "login"
    st.session_state.nickname = ""
    st.session_state.group = ""
    st.session_state.questions = []
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.user_answer = ""
    st.session_state.current_options = []
    st.session_state.incorrect_answers = [] # Для режима обзора ошибок
    st.session_state.timer_enabled = False
    st.session_state.seconds_per_question = 30
    st.session_state.question_start_time = 0

initialize_leaderboard()

# --- Логика отображения страниц ---
st.set_page_config(layout="centered")
st.title("🎓 Интерактивный тест по PDF")

# --- СТРАНИЦА 1: ЛОГИН ---
if st.session_state.page == "login":
    st.subheader("Добро пожаловать!")
    with st.form("login_form"):
        nickname = st.text_input("ФИО:")
        group = st.text_input("Введите вашу группу:")
        submitted = st.form_submit_button("Войти и начать тест")
        if submitted:
            if nickname and group:
                st.session_state.nickname = nickname
                st.session_state.group = group
                st.session_state.page = "upload"
                st.rerun()
            else:
                st.error("Пожалуйста, заполните все поля.")
    st.divider()
    load_leaderboard()

# --- СТРАНИЦА 2: НАСТРОЙКА ТЕСТА И ЗАГРУЗКА ---
elif st.session_state.page == "upload":
    st.write(f"Привет, **{st.session_state.nickname}** из группы **{st.session_state.group}**!")
    st.write("Загрузите PDF-файл и настройте тест.")
    
    uploaded_file = st.file_uploader("Выберите PDF файл", type="pdf", label_visibility="collapsed")
    
    if uploaded_file:
        with st.spinner('Пожалуйста, подождите. Идет обработка PDF...'):
            pdf_stream = io.BytesIO(uploaded_file.read())
            text = extract_text_from_pdf_pypdf(pdf_stream)
        if text:
            all_questions = parse_questions_from_text(text)
            if all_questions:
                st.success(f"Файл успешно обработан! Найдено вопросов: {len(all_questions)}")
                
                # --- НОВЫЕ НАСТРОЙКИ ТЕСТА ---
                st.divider()
                st.subheader("⚙️ Настройки теста")
                
                num_questions_slider = st.slider(
                    "1. Выберите количество вопросов:", 
                    min_value=5, max_value=len(all_questions), 
                    value=min(40, len(all_questions)), step=5
                )

                timer_enabled_checkbox = st.checkbox("2. Включить таймер на вопросы?")
                seconds_per_question_input = 30
                if timer_enabled_checkbox:
                    seconds_per_question_input = st.number_input(
                        "Время на один вопрос (секунд):", 
                        min_value=10, max_value=120, value=30, step=5
                    )
                # --- КОНЕЦ НАСТРОЕК ---
                
                if st.button("Начать тест!", type="primary"):
                    st.session_state.questions = random.sample(all_questions, num_questions_slider)
                    st.session_state.timer_enabled = timer_enabled_checkbox
                    st.session_state.seconds_per_question = seconds_per_question_input
                    
                    st.session_state.page = "quiz"
                    # Готовим первый вопрос
                    first_question_options = st.session_state.questions[0]['options'][:]
                    random.shuffle(first_question_options)
                    st.session_state.current_options = first_question_options
                    st.session_state.question_start_time = time.time() # Запускаем таймер для первого вопроса
                    st.rerun()
            else:
                st.warning("В файле не найдены вопросы в ожидаемом формате.")

# --- СТРАНИЦА 3: ТЕСТ ---
elif st.session_state.page == "quiz":
    if st.session_state.current_question_index < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.current_question_index]
        total_questions = len(st.session_state.questions)
        
        # Отображение прогресса и счета
        progress_value = (st.session_state.current_question_index) / total_questions
        st.progress(progress_value, text=f"Вопрос {st.session_state.current_question_index + 1}/{total_questions}")
        st.info(f"Текущий счет: {st.session_state.score}")

        st.subheader(q["question"])
        
        # Логика таймера
        time_is_up = False
        if st.session_state.timer_enabled:
            elapsed_time = time.time() - st.session_state.question_start_time
            remaining_time = st.session_state.seconds_per_question - elapsed_time
            if remaining_time > 0:
                st.sidebar.metric("Осталось времени", f"{int(remaining_time)} сек")
            else:
                time_is_up = True
                st.sidebar.error("Время вышло!")

        if not st.session_state.answer_submitted:
            # Если время вышло, блокируем ответ
            if time_is_up:
                st.warning("Время на ответ истекло. Нажмите 'Дальше', чтобы перейти к следующему вопросу.")
                if st.button("Дальше"):
                    st.session_state.incorrect_answers.append({
                        'question': q['question'], 'your_answer': "Время вышло", 'correct_answer': q['correct_answer']
                    })
                    st.session_state.current_question_index += 1
                    # Готовим следующий вопрос
                    if st.session_state.current_question_index < total_questions:
                        next_q = st.session_state.questions[st.session_state.current_question_index]
                        next_options = next_q['options'][:]
                        random.shuffle(next_options)
                        st.session_state.current_options = next_options
                        st.session_state.question_start_time = time.time()
                    st.rerun()
            else:
                st.session_state.user_answer = st.radio("Выберите ответ:", st.session_state.current_options, key=f"q_{st.session_state.current_question_index}")
                if st.button("Ответить"):
                    st.session_state.answer_submitted = True
                    is_correct = st.session_state.user_answer == q["correct_answer"]
                    if is_correct:
                        st.session_state.score += 1
                    else:
                        st.session_state.incorrect_answers.append({
                            'question': q['question'], 'your_answer': st.session_state.user_answer, 'correct_answer': q['correct_answer']
                        })
                    st.rerun()
        else:
            if st.session_state.user_answer == q["correct_answer"]:
                st.success(f"Правильно! Ваш ответ: {st.session_state.user_answer}")
            else:
                st.error(f"Неправильно. Ваш ответ: {st.session_state.user_answer}")
                st
