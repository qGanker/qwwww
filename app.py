import streamlit as st
from pypdf import PdfReader
import random
import io
import pandas as pd
import os

# --- Константы и функции ---

LEADERBOARD_FILE = "leaderboard.csv"

def initialize_leaderboard():
    """Создает CSV-файл для таблицы лидеров, если он не существует."""
    if not os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "w", newline="") as f:
            f.write("Ник,Группа,Процент,Правильных,Всего\n")

def save_score(nickname, group, score, total):
    """Сохраняет результат пользователя в CSV-файл."""
    percentage = round((score / total) * 100)
    # Используем 'a' (append) для добавления новой строки в конец файла
    with open(LEADERBOARD_FILE, "a", newline="", encoding='utf-8') as f:
        f.write(f"{nickname},{group},{percentage},{score},{total}\n")

def load_leaderboard():
    """Загружает и отображает таблицу лидеров."""
    if os.path.exists(LEADERBOARD_FILE) and os.path.getsize(LEADERBOARD_FILE) > 20: # Проверка на непустой файл
        try:
            df = pd.read_csv(LEADERBOARD_FILE)
            df_sorted = df.sort_values(by="Процент", ascending=False).reset_index(drop=True)
            st.subheader("🏆 Таблица лидеров (Топ-10)")
            st.dataframe(df_sorted.head(10))
        except pd.errors.EmptyDataError:
            st.info("Таблица лидеров пока пуста.")
        except Exception as e:
            st.error(f"Не удалось загрузить таблицу лидеров: {e}")
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

# --- Инициализация состояния сессии ---
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

# Создаем файл таблицы лидеров при первом запуске
initialize_leaderboard()

# --- Логика отображения страниц ---
st.set_page_config(layout="centered")
st.title("🎓 Интерактивный тест по PDF")

# --- СТРАНИЦА 1: ЛОГИН ---
if st.session_state.page == "login":
    st.subheader("Добро пожаловать!")
    with st.form("login_form"):
        nickname = st.text_input("Введите ваш ник:")
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

# --- СТРАНИЦА 2: ЗАГРУЗКА ФАЙЛА ---
elif st.session_state.page == "upload":
    st.write(f"Привет, **{st.session_state.nickname}** из группы **{st.session_state.group}**!")
    st.write("Загрузите PDF-файл, чтобы начать тест.")
    
    uploaded_file = st.file_uploader("Выберите PDF файл", type="pdf", label_visibility="collapsed")
    if uploaded_file:
        with st.spinner('Пожалуйста, подождите. Идет обработка вашего PDF-файла...'):
            pdf_stream = io.BytesIO(uploaded_file.read())
            text = extract_text_from_pdf_pypdf(pdf_stream)
        if text:
            all_questions = parse_questions_from_text(text)
            if all_questions:
                st.success(f"Файл успешно обработан! Найдено вопросов: {len(all_questions)}")
                st.session_state.questions = random.sample(all_questions, min(40, len(all_questions)))
                if st.button("Начать тест!", type="primary"):
                    st.session_state.page = "quiz"
                    first_question_options = st.session_state.questions[0]['options'][:]
                    random.shuffle(first_question_options)
                    st.session_state.current_options = first_question_options
                    st.rerun()
            else:
                st.warning("В файле не найдены вопросы в ожидаемом формате.")

# --- СТРАНИЦА 3: ТЕСТ ---
elif st.session_state.page == "quiz":
    if st.session_state.current_question_index < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.current_question_index]
        progress_value = (st.session_state.current_question_index) / len(st.session_state.questions)
        st.progress(progress_value, text=f"Вопрос {st.session_state.current_question_index + 1}/{len(st.session_state.questions)}")
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
                if st.session_state.current_question_index < len(st.session_state.questions):
                    next_question_options = st.session_state.questions[st.session_state.current_question_index]['options'][:]
                    random.shuffle(next_question_options)
                    st.session_state.current_options = next_question_options
                st.rerun()
    else:
        st.session_state.page = "results"
        st.rerun()

# --- СТРАНИЦА 4: РЕЗУЛЬТАТЫ ---
elif st.session_state.page == "results":
    st.header("Тест завершен!")
    total = len(st.session_state.questions)
    score = st.session_state.score
    
    percentage = round((score / total) * 100) if total > 0 else 0
    
    st.success(f"Ваш результат: {score} из {total} ({percentage}%)")
    
    # Сохраняем результат в таблицу лидеров
    save_score(st.session_state.nickname, st.session_state.group, score, total)
    
    st.divider()
    load_leaderboard()
    st.divider()

    if st.button("Пройти тест еще раз"):
        # Сбрасываем только прогресс теста, оставляя логин
        st.session_state.page = "upload"
        st.session_state.questions = []
        st.session_state.current_question_index = 0
        st.session_state.score = 0
        st.session_state.answer_submitted = False
        st.session_state.current_options = []
        st.rerun()
