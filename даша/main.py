
from html import escape

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from database import create_database, get_connection
from excel import create_excel


create_database()

app = FastAPI(title="Система учебных поручений")


def get_page(content: str) -> str:
    """Общая HTML-страница приложения."""
    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Учебные поручения</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 950px;
                margin: 40px auto;
                padding: 0 20px;
                background: #f5f6fa;
            }}

            h1, h2 {{
                color: #26344a;
            }}

            .container {{
                background: white;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 20px;
            }}

            input, select {{
                display: block;
                width: 100%;
                box-sizing: border-box;
                padding: 10px;
                margin: 7px 0 15px;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 15px;
            }}

            input::placeholder {{
                color: #999;
                opacity: 1;
            }}

            input:focus {{
                outline: none;
                border-color: #315f9b;
            }}

            button, .button {{
                display: inline-block;
                padding: 11px 18px;
                background: #315f9b;
                color: white;
                border: none;
                border-radius: 5px;
                text-decoration: none;
                cursor: pointer;
                font-size: 15px;
                margin: 5px 5px 5px 0;
            }}

            button:hover, .button:hover {{
                background: #244875;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th, td {{
                border: 1px solid #ddd;
                padding: 9px;
                text-align: left;
            }}

            th {{
                background: #e8edf5;
            }}

            .message {{
                padding: 12px;
                background: #e8f3e8;
                border-radius: 5px;
                margin-bottom: 15px;
            }}

            .error {{
                padding: 12px;
                background: #fbe8e8;
                border-radius: 5px;
                margin-bottom: 15px;
            }}
        </style>
    </head>

    <body>
        {content}
    </body>
    </html>
    """


def number_or_default(value, default=0, number_type=float):
    """Преобразует пустое числовое поле в значение по умолчанию."""
    if value is None or str(value).strip() == "":
        return number_type(default)

    return number_type(value)


def check_teacher_workload(teacher_id, academic_year):
    """Проверяет годовую плановую нагрузку преподавателя."""
    conn = get_connection()

    try:
        teacher = conn.execute("""
            SELECT
                teachers.full_name,
                teachers.rate,
                positions.annual_full_time_hours
            FROM teachers
            JOIN positions
                ON teachers.position_id = positions.position_id
            WHERE teachers.teacher_id = ?
        """, (teacher_id,)).fetchone()

        if teacher is None:
            return {
                "status": "error",
                "message": "Преподаватель не найден."
            }

        year = conn.execute("""
            SELECT academic_year
            FROM academic_years
            WHERE academic_year = ?
        """, (academic_year,)).fetchone()

        if year is None:
            return {
                "status": "error",
                "message": "Учебный год не найден."
            }

        planned_hours = conn.execute("""
            SELECT COALESCE(SUM(hours_sem1 + hours_sem2), 0)
            FROM workload_hours
            WHERE teacher_id = ?
              AND academic_year = ?
              AND record_type = 'План'
        """, (teacher_id, academic_year)).fetchone()[0]

        limit_hours = (
            teacher["annual_full_time_hours"] * teacher["rate"]
        )

        if planned_hours > limit_hours:
            return {
                "status": "error",
                "message": (
                    f"Перегрузка у преподавателя {teacher['full_name']}: "
                    f"план составляет {planned_hours} ч., "
                    f"допустимо {limit_hours} ч."
                )
            }

        return {
            "status": "success",
            "message": (
                f"Норма не превышена у преподавателя {teacher['full_name']}: "
                f"план составляет {planned_hours} ч., "
                f"допустимо {limit_hours} ч."
            )
        }

    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
def home():
    """Главная страница с формой."""

    content = """
    <div class="container">
        <h1>Система учебных поручений</h1>

        <p>
            Бета-версия для внесения и просмотра учебной нагрузки преподавателей.
        </p>

        <form action="/save" method="post">

            <h2>Данные преподавателя</h2>

            <label>ФИО преподавателя</label>
            <input
                type="text"
                name="full_name"
                placeholder="Введите ФИО"
                required
            >

            <label>Дата рождения</label>
            <input
                type="date"
                name="birth_date"
            >

            <label>Учёная степень</label>
            <input
                type="text"
                name="degree"
                placeholder="Например, к.ф.-м.н."
            >

            <label>Учёное звание</label>
            <input
                type="text"
                name="academic_title"
                placeholder="Например, профессор"
            >

            <label>Стаж в вузе, лет</label>
            <input
                type="number"
                name="years_in_university"
                min="0"
                step="1"
                placeholder="0"
            >

            <label>Кафедра</label>
            <input
                type="text"
                name="department"
                placeholder="Введите название кафедры"
                required
            >

            <label>Институт</label>
            <input
                type="text"
                name="institute"
                placeholder="Введите название института"
            >

            <label>Должность</label>
            <input
                type="text"
                name="position"
                placeholder="Например, доцент"
                required
            >

            <label>Предельная учебная нагрузка, ч</label>
            <input
                type="number"
                name="max_teaching_hours"
                min="0"
                step="0.5"
                placeholder="800"
            >

            <label>Годовой объём на полную ставку, ч</label>
            <input
                type="number"
                name="annual_full_time_hours"
                min="0.5"
                step="0.5"
                placeholder="1524"
            >

            <label>Доля ставки</label>
            <input
                type="number"
                name="rate"
                min="0.1"
                max="5"
                step="0.1"
                placeholder="Например, 1"
                required
            >

            <h2>Учебное поручение</h2>

            <label>Учебный год</label>
            <input
                type="text"
                name="academic_year"
                placeholder="Например, 2026/2027"
                required
            >

            <label>Дисциплина</label>
            <input
                type="text"
                name="discipline"
                placeholder="Введите название дисциплины"
                required
            >

            <label>Группа</label>
            <input
                type="text"
                name="group_name"
                placeholder="Введите номер группы"
            >

            <label>Количество студентов</label>
            <input
                type="number"
                name="student_count"
                min="0"
                step="1"
                placeholder="0"
            >

            <label>Семестр</label>
            <select name="semester">
                <option value="1">Первый</option>
                <option value="2">Второй</option>
            </select>

            <h2>Количество часов</h2>

            <label>Лекции</label>
            <input
                type="number"
                name="lecture_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Практические занятия</label>
            <input
                type="number"
                name="practice_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Лабораторные занятия</label>
            <input
                type="number"
                name="laboratory_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Консультации</label>
            <input
                type="number"
                name="consultation_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Экзамены</label>
            <input
                type="number"
                name="exam_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Курсовые работы</label>
            <input
                type="number"
                name="coursework_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>ВКР</label>
            <input
                type="number"
                name="thesis_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <label>Другие часы</label>
            <input
                type="number"
                name="other_hours"
                min="0"
                step="0.5"
                placeholder="0"
            >

            <button type="submit">Сохранить поручение</button>

        </form>
    </div>

    <div class="container">
        <h2>Работа с данными</h2>

        <a class="button" href="/records">
            Посмотреть записи
        </a>

        <a class="button" href="/export">
            Выгрузить Excel
        </a>
    </div>
    """

    return get_page(content)


@app.post("/save", response_class=HTMLResponse)
def save_assignment(
    full_name: str = Form(...),
    birth_date: str = Form(""),
    degree: str = Form(""),
    academic_title: str = Form(""),
    years_in_university: str = Form(""),
    department: str = Form(...),
    institute: str = Form(""),
    position: str = Form(...),
    max_teaching_hours: str = Form(""),
    annual_full_time_hours: str = Form(""),
    rate: str = Form(...),
    academic_year: str = Form(...),
    discipline: str = Form(...),
    group_name: str = Form(""),
    student_count: str = Form(""),
    semester: str = Form("1"),
    lecture_hours: str = Form(""),
    practice_hours: str = Form(""),
    laboratory_hours: str = Form(""),
    consultation_hours: str = Form(""),
    exam_hours: str = Form(""),
    coursework_hours: str = Form(""),
    thesis_hours: str = Form(""),
    other_hours: str = Form(""),
):
    """Сохраняет преподавателя и его учебное поручение."""

    conn = get_connection()

    try:
        # Преобразование пустых числовых полей в числа
        years_in_university = number_or_default(
            years_in_university, 0, int
        )

        max_teaching_hours = number_or_default(
            max_teaching_hours, 800
        )

        annual_full_time_hours = number_or_default(
            annual_full_time_hours, 1524
        )

        student_count = number_or_default(
            student_count, 0, int
        )

        semester = number_or_default(
            semester, 1, int
        )

        rate = number_or_default(rate, 0)

        lecture_hours = number_or_default(lecture_hours, 0)
        practice_hours = number_or_default(practice_hours, 0)
        laboratory_hours = number_or_default(laboratory_hours, 0)
        consultation_hours = number_or_default(consultation_hours, 0)
        exam_hours = number_or_default(exam_hours, 0)
        coursework_hours = number_or_default(coursework_hours, 0)
        thesis_hours = number_or_default(thesis_hours, 0)
        other_hours = number_or_default(other_hours, 0)

        # Очистка текстовых полей
        full_name = full_name.strip()
        department = department.strip()
        institute = institute.strip()
        position = position.strip()
        academic_year = academic_year.strip()
        discipline = discipline.strip()
        group_name = group_name.strip()
        degree = degree.strip()
        academic_title = academic_title.strip()

        if not all([
            full_name,
            department,
            position,
            academic_year,
            discipline
        ]):
            raise ValueError("Заполните обязательные поля.")

        if rate <= 0:
            raise ValueError("Ставка должна быть больше нуля.")

        if max_teaching_hours < 0 or annual_full_time_hours <= 0:
            raise ValueError("Проверьте нормы часов должности.")

        if years_in_university < 0 or student_count < 0:
            raise ValueError(
                "Стаж и количество студентов не могут быть отрицательными."
            )

        if semester not in (1, 2):
            raise ValueError("Укажите первый или второй семестр.")

        hours = [
            lecture_hours,
            practice_hours,
            laboratory_hours,
            consultation_hours,
            exam_hours,
            coursework_hours,
            thesis_hours,
            other_hours
        ]

        if any(hour < 0 for hour in hours):
            raise ValueError(
                "Количество часов не может быть отрицательным."
            )

        total_hours = sum(hours)

        # Кафедра
        conn.execute("""
            INSERT OR IGNORE INTO departments
                (department_name, institute)
            VALUES (?, ?)
        """, (department, institute))

        department_row = conn.execute("""
            SELECT department_id
            FROM departments
            WHERE department_name = ? AND institute = ?
        """, (department, institute)).fetchone()

        department_id = department_row["department_id"]

        # Должность
        conn.execute("""
            INSERT OR IGNORE INTO positions
                (position_name, max_teaching_hours,
                 annual_full_time_hours)
            VALUES (?, ?, ?)
        """, (
            position,
            max_teaching_hours,
            annual_full_time_hours
        ))

        position_row = conn.execute("""
            SELECT position_id
            FROM positions
            WHERE position_name = ?
        """, (position,)).fetchone()

        position_id = position_row["position_id"]

        conn.execute("""
            UPDATE positions
            SET max_teaching_hours = ?,
                annual_full_time_hours = ?
            WHERE position_id = ?
        """, (
            max_teaching_hours,
            annual_full_time_hours,
            position_id
        ))

        # Учебный год
        conn.execute("""
            INSERT OR IGNORE INTO academic_years
                (academic_year, is_closed)
            VALUES (?, 0)
        """, (academic_year,))

        year_row = conn.execute("""
            SELECT is_closed
            FROM academic_years
            WHERE academic_year = ?
        """, (academic_year,)).fetchone()

        if year_row["is_closed"]:
            raise ValueError("Этот учебный год закрыт.")

        # Преподаватель
        teacher = conn.execute("""
            SELECT teacher_id
            FROM teachers
            WHERE full_name = ? AND department_id = ?
        """, (full_name, department_id)).fetchone()

        if teacher is None:
            cursor = conn.execute("""
                INSERT INTO teachers (
                    department_id,
                    position_id,
                    full_name,
                    birth_date,
                    degree,
                    academic_title,
                    rate,
                    years_in_university,
                    is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                department_id,
                position_id,
                full_name,
                birth_date or None,
                degree,
                academic_title,
                rate,
                years_in_university
            ))

            teacher_id = cursor.lastrowid

        else:
            teacher_id = teacher["teacher_id"]

            conn.execute("""
                UPDATE teachers
                SET position_id = ?,
                    birth_date = ?,
                    degree = ?,
                    academic_title = ?,
                    rate = ?,
                    years_in_university = ?
                WHERE teacher_id = ?
            """, (
                position_id,
                birth_date or None,
                degree,
                academic_title,
                rate,
                years_in_university,
                teacher_id
            ))

        # Учебное поручение
        conn.execute("""
            INSERT INTO teaching_assignments (
                teacher_id,
                academic_year,
                discipline,
                group_code,
                student_count,
                semester,
                lecture_hours,
                practice_hours,
                laboratory_hours,
                consultation_hours,
                exam_hours,
                coursework_hours,
                thesis_hours,
                other_hours,
                total_hours
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            teacher_id,
            academic_year,
            discipline,
            group_name,
            student_count,
            semester,
            lecture_hours,
            practice_hours,
            laboratory_hours,
            consultation_hours,
            exam_hours,
            coursework_hours,
            thesis_hours,
            other_hours,
            total_hours
        ))

        # Вид работы для учёта плановой нагрузки
        conn.execute("""
            INSERT OR IGNORE INTO work_types
                (section, work_name, unit, uses_norm)
            VALUES (?, ?, ?, 0)
        """, (
            "I. Учебная нагрузка",
            "Учебное поручение",
            "Час"
        ))

        work_type = conn.execute("""
            SELECT work_type_id
            FROM work_types
            WHERE section = ? AND work_name = ?
        """, (
            "I. Учебная нагрузка",
            "Учебное поручение"
        )).fetchone()

        work_type_id = work_type["work_type_id"]

        hours_sem1 = total_hours if semester == 1 else 0
        hours_sem2 = total_hours if semester == 2 else 0

        conn.execute("""
            INSERT INTO workload_hours (
                teacher_id,
                academic_year,
                work_type_id,
                record_type,
                hours_sem1,
                hours_sem2,
                comment
            )
            VALUES (?, ?, ?, 'План', ?, ?, ?)
        """, (
            teacher_id,
            academic_year,
            work_type_id,
            hours_sem1,
            hours_sem2,
            f"Поручение: {discipline}, группа {group_name}"
        ))

        conn.commit()

        result = check_teacher_workload(
            teacher_id,
            academic_year
        )

        message_class = (
            "message" if result["status"] == "success"
            else "error"
        )

        content = f"""
        <div class="container">
            <h1>Данные сохранены</h1>

            <p class="message">
                Преподаватель и учебное поручение успешно добавлены
                в базу данных.
            </p>

            <p class="{message_class}">
                {escape(result["message"])}
            </p>

            <a class="button" href="/">Вернуться к форме</a>
            <a class="button" href="/records">Посмотреть записи</a>
        </div>
        """

        return get_page(content)

    except ValueError as error:
        conn.rollback()

        return get_page(f"""
        <div class="container">
            <h1>Ошибка ввода</h1>
            <p class="error">{escape(str(error))}</p>
            <a class="button" href="/">Вернуться к форме</a>
        </div>
        """)

    except Exception as error:
        conn.rollback()
        print("ОШИБКА СОХРАНЕНИЯ:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить данные."
        )

    finally:
        conn.close()


@app.get("/records", response_class=HTMLResponse)
def show_records():
    """Показывает сохранённые учебные поручения."""

    conn = get_connection()

    try:
        assignments = conn.execute("""
            SELECT
                teaching_assignments.*,
                teachers.full_name,
                departments.department_name
            FROM teaching_assignments
            JOIN teachers
                ON teaching_assignments.teacher_id = teachers.teacher_id
            JOIN departments
                ON teachers.department_id = departments.department_id
            ORDER BY teaching_assignments.assignment_id DESC
        """).fetchall()

        rows = ""

        for assignment in assignments:
            rows += f"""
            <tr>
                <td>{escape(assignment["full_name"])}</td>
                <td>{escape(assignment["department_name"])}</td>
                <td>{escape(assignment["academic_year"])}</td>
                <td>{escape(assignment["discipline"])}</td>
                <td>{escape(assignment["group_code"] or "")}</td>
                <td>{assignment["semester"]}</td>
                <td>{assignment["total_hours"]}</td>
            </tr>
            """

        if not rows:
            rows = """
            <tr>
                <td colspan="7">Пока нет сохранённых записей.</td>
            </tr>
            """

        content = f"""
        <div class="container">
            <h1>Сохранённые поручения</h1>

            <table>
                <tr>
                    <th>Преподаватель</th>
                    <th>Кафедра</th>
                    <th>Учебный год</th>
                    <th>Дисциплина</th>
                    <th>Группа</th>
                    <th>Семестр</th>
                    <th>Всего часов</th>
                </tr>

                {rows}
            </table>

            <br>

            <a class="button" href="/">Вернуться к форме</a>
            <a class="button" href="/export">Выгрузить Excel</a>
        </div>
        """

        return get_page(content)

    finally:
        conn.close()


@app.get("/export")
def export_excel():
    """Выгружает все 10 таблиц в Excel."""

    try:
        excel_file = create_excel()

        return StreamingResponse(
            excel_file,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers={
                "Content-Disposition":
                    'attachment; filename="uchebnye_porucheniya.xlsx"'
            }
        )

    except Exception as error:
        print("ОШИБКА ВЫГРУЗКИ:", repr(error))

        raise HTTPException(
            status_code=500,
            detail="Не удалось сформировать Excel-файл."
        )
