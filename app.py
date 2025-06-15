import streamlit as st
from pypdf import PdfReader
import random
import io

# --- Функции для обработки текста и оценки ---
def parse_questions_from_text(text):
    """
    Финальная версия: корректно обрабатывает многострочные вопросы и многострочные варианты ответов.
    """
    text_no_pages = "\n".join([line for line in text.split('\n') if "--- PAGE" not in line])
    question_blocks = text_no_pages.strip().split('?')
    parsed_questions = []

    for block in question_blocks:
        lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
        if not lines:
            continue

        first_option_index = -1
        for i, line in enumerate(lines):
            if line.startswith('+') or line.startswith('-'):
                first_option_index = i
                break
        
        if first_option_index == -1:
            continue
            
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
                if is_correct_buffer:
                    correct_answer = full_option_text
                current_option_parts = []

            if is_new_option_line:
                is_correct_buffer = line.startswith('+')
            
            current_option_parts.append(line.lstrip('+- ').strip())

        if current_option_parts:
            full_option_text = " ".join(current_option_parts)
            options.append(full_option_text)
            if is_correct_buffer:
                correct_answer = full_option_text
        
        if question_text and options and correct_answer:
            parsed_questions.append({
                "question": question_text,
                "options": options,
                "correct_answer": correct_answer
            })
            
    return parsed_questions


def extract_text_from_pdf_pypdf(pdf_stream):
    """Извлекает текст с помощью библиотеки pypdf."""
    try:
        reader = PdfReader(pdf_stream)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n" 
        return full_text
    except Exception as e:
        st.error(f"Ошибка при чтении PDF с помощью pypdf: {e}")
        return None

def get_grade(score, total_questions):
    """Возвращает оценку по пятибалльной шкале."""
    if total_questions == 0:
        return 0, "Тест не был пройден."
    percentage = (score / total_questions) * 100
    if percentage >= 90: return 5, "Отлично! 🎉"
    elif percentage >= 75: return 4, "Хорошо! 👍"
    elif percentage >= 50: return 3, "Удовлетворительно. 🤔"
    else: return 2, "Неудовлетворительно. Попробуйте еще раз. 🔁"

# --- Инициализация состояния сессии ---
if 'quiz_started' not in st.session_state:
    st.session_state.quiz_started = False
    st.session_state.questions = []
    st.session_state.current_question_index = 0
    st.session_state.score = 0
    st.session_state.answer_submitted = False
    st.session_state.user_answer = ""
    # Эта строка инициализирует ключ в памяти сессии
    st.session_state.current_options = []

# --- Интерфейс приложения ---
st.set_page_config(layout="centered")
st.title("🎓 Интерактивный тест по PDF")

if not st.session_state.quiz_started:
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
                    st.session_state.quiz_started = True
                    # Готовим и перемешиваем варианты для первого вопроса
                    first_question_options = st.session_state.questions[0]['options'][:]
                    random.shuffle(first_question_options)
                    st.session_state.current_options = first_question_options
                    st.rerun()
            else:
                st.warning("В файле не найдены вопросы в ожидаемом формате.")
else:
    if st.session_state.current_question_index < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.current_question_index]
        progress_value = (st.session_state.current_question_index) / len(st.session_state.questions)
        st.progress(progress_value, text=f"Вопрос {st.session_state.current_question_index + 1}/{len(st.session_state.questions)}")
        st.subheader(q["question"])
        if not st.session_state.answer_submitted:
            # Используем сохраненный, "замороженный" порядок вариантов
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
                # Готовим и перемешиваем варианты для следующего вопроса
                if st.session_state.current_question_index < len(st.session_state.questions):
                    next_question_options = st.session_state.questions[st.session_state.current_question_index]['options'][:]
                    random.shuffle(next_question_options)
                    st.session_state.current_options = next_question_options
                st.rerun()
    else:
        st.header("Тест завершен!")
        total = len(st.session_state.questions)
        score = st.session_state.score
        grade, comment = get_grade(score, total)
        st.success(f"Ваш результат: {score} из {total} правильных ответов.")
        st.title(f"Ваша оценка: {grade}")
        st.info(comment)
        if st.button("Пройти еще раз"):
            # Сбрасываем состояние для нового теста
            st.session_state.quiz_started = False
            st.session_state.questions = []
            st.session_state.current_question_index = 0
            st.session_state.score = 0
            st.session_state.answer_submitted = False
            st.session_state.current_options = []
            st.rerun()
