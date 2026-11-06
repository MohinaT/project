import sqlite3

# Имя файла базы данных.
DB_NAME = "university_reports_demo.db"

# Годовая норма для полной ставки.
ANNUAL_HOURS = 1524
ACADEMIC_YEAR = "2026/2027"


# SQL-запросы для создания всех 10 таблиц.
CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name TEXT NOT NULL,
    institute TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (department_name, institute)
);

CREATE TABLE IF NOT EXISTS positions (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_name TEXT NOT NULL UNIQUE,
    max_teaching_hours REAL NOT NULL,
    annual_full_time_hours REAL NOT NULL DEFAULT 1524
);

CREATE TABLE IF NOT EXISTS academic_years (
    academic_year TEXT PRIMARY KEY,
    is_closed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS work_types (
    work_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,
    work_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    uses_norm INTEGER DEFAULT 0,
    UNIQUE (section, work_name)
);

CREATE TABLE IF NOT EXISTS teachers (
    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    birth_date TEXT,
    degree TEXT,
    academic_title TEXT,
    rate REAL NOT NULL,
    years_in_university INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (position_id) REFERENCES positions(position_id)
);

CREATE TABLE IF NOT EXISTS users (
    login TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    teacher_id INTEGER,
    department_id INTEGER,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS time_norms (
    norm_id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_type_id INTEGER NOT NULL,
    position_id INTEGER,
    norm_value REAL NOT NULL,
    norm_basis TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    source_document TEXT,
    FOREIGN KEY (work_type_id) REFERENCES work_types(work_type_id),
    FOREIGN KEY (position_id) REFERENCES positions(position_id)
);

CREATE TABLE IF NOT EXISTS teaching_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    academic_year TEXT NOT NULL,
    discipline TEXT NOT NULL,
    group_code TEXT NOT NULL,
    student_count INTEGER DEFAULT 0,
    semester INTEGER NOT NULL,
    lecture_hours REAL DEFAULT 0,
    practice_hours REAL DEFAULT 0,
    laboratory_hours REAL DEFAULT 0,
    consultation_hours REAL DEFAULT 0,
    exam_hours REAL DEFAULT 0,
    coursework_hours REAL DEFAULT 0,
    thesis_hours REAL DEFAULT 0,
    total_hours REAL DEFAULT 0,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
    FOREIGN KEY (academic_year) REFERENCES academic_years(academic_year)
);

CREATE TABLE IF NOT EXISTS workload_hours (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    academic_year TEXT NOT NULL,
    work_type_id INTEGER NOT NULL,
    record_type TEXT NOT NULL,
    hours_sem1 REAL NOT NULL DEFAULT 0,
    hours_sem2 REAL NOT NULL DEFAULT 0,
    comment TEXT,
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
    FOREIGN KEY (academic_year) REFERENCES academic_years(academic_year),
    FOREIGN KEY (work_type_id) REFERENCES work_types(work_type_id)
);

CREATE TABLE IF NOT EXISTS documents (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    academic_year TEXT NOT NULL,
    document_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    formatted_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Черновик',
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id),
    FOREIGN KEY (academic_year) REFERENCES academic_years(academic_year)
);
"""


def create_database():
    """Создаёт базу данных и таблицы, если их ещё нет."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Включаем проверку внешних ключей.
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.executescript(CREATE_TABLES)

    conn.commit()
    conn.close()


def check_teacher_workload(teacher_id, academic_year):
    """Проверяет, не превышает ли план часов годовую норму преподавателя."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Получаем ФИО, ставку и годовую норму из таблицы должностей.
    cursor.execute("""
        SELECT teachers.full_name,
               teachers.rate,
               positions.annual_full_time_hours
        FROM teachers
        JOIN positions
            ON teachers.position_id = positions.position_id
        WHERE teachers.teacher_id = ?
    """, (teacher_id,))

    teacher = cursor.fetchone()

    if teacher is None:
        conn.close()
        return {
            "status": "error",
            "message": "Преподаватель не найден."
        }

    full_name = teacher[0]
    rate = teacher[1]
    annual_hours = teacher[2]

    # Проверяем, что указанный учебный год есть в базе.
    cursor.execute(
        "SELECT academic_year FROM academic_years WHERE academic_year = ?",
        (academic_year,)
    )
    year = cursor.fetchone()

    if year is None:
        conn.close()
        return {
            "status": "error",
            "message": "Учебный год не найден."
        }

    # Считаем плановые часы за оба семестра только за выбранный год.
    cursor.execute("""
        SELECT COALESCE(SUM(hours_sem1 + hours_sem2), 0)
        FROM workload_hours
        WHERE teacher_id = ?
          AND academic_year = ?
          AND record_type = 'План'
    """, (teacher_id, academic_year))

    planned_hours = cursor.fetchone()[0]

    # Лимит зависит от годовой нормы должности и ставки преподавателя.
    limit_hours = annual_hours * rate

    conn.close()

    if planned_hours > limit_hours:
        return {
            "status": "error",
            "message": (
                f"Перегрузка у преподавателя {full_name}: "
                f"план составляет {planned_hours} ч., "
                f"допустимо {limit_hours} ч."
            )
        }

    return {
        "status": "success",
        "message": (
            f"Норма не превышена у преподавателя {full_name}: "
            f"план составляет {planned_hours} ч., "
            f"допустимо {limit_hours} ч."
        )
    }


def add_test_data():
    """Добавляет тестовую кафедру, должность, год, вид работы и преподавателя."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    # Добавляем кафедру.
    cursor.execute("""
        INSERT OR IGNORE INTO departments (department_name, institute)
        VALUES (?, ?)
    """, ("Технической физики", "Физико-технологический институт"))

    cursor.execute("""
        SELECT department_id
        FROM departments
        WHERE department_name = ? AND institute = ?
    """, ("Технической физики", "Физико-технологический институт"))
    department_id = cursor.fetchone()[0]

    # Добавляем должность с годовой нормой 1524 часа.
    cursor.execute("""
        INSERT OR IGNORE INTO positions
            (position_name, max_teaching_hours, annual_full_time_hours)
        VALUES (?, ?, ?)
    """, ("доцент", 800, ANNUAL_HOURS))

    cursor.execute(
        "SELECT position_id FROM positions WHERE position_name = ?",
        ("доцент",)
    )
    position_id = cursor.fetchone()[0]

    # Добавляем учебный год.
    cursor.execute(
        "INSERT OR IGNORE INTO academic_years (academic_year) VALUES (?)",
        (ACADEMIC_YEAR,)
    )

    # Добавляем вид работы, для которого записываем часы.
    cursor.execute("""
        INSERT OR IGNORE INTO work_types (section, work_name, unit, uses_norm)
        VALUES (?, ?, ?, 0)
    """, ("I. Учебная нагрузка", "Чтение лекций", "Час"))

    cursor.execute("""
        SELECT work_type_id
        FROM work_types
        WHERE section = ? AND work_name = ?
    """, ("I. Учебная нагрузка", "Чтение лекций"))
    work_type_id = cursor.fetchone()[0]

    # Проверяем, есть ли уже такой преподаватель.
    cursor.execute("""
        SELECT teacher_id
        FROM teachers
        WHERE full_name = ? AND department_id = ?
    """, ("Александров Олег Евгеньевич", department_id))

    teacher = cursor.fetchone()

    if teacher is None:
        cursor.execute("""
            INSERT INTO teachers
                (department_id, position_id, full_name, rate,
                 years_in_university, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (department_id, position_id,
              "Александров Олег Евгеньевич", 1.0, 8))
        teacher_id = cursor.lastrowid
    else:
        teacher_id = teacher[0]
        cursor.execute("""
            UPDATE teachers
            SET position_id = ?, rate = 1.0, is_active = 1
            WHERE teacher_id = ?
        """, (position_id, teacher_id))

    # Удаляем старую демонстрационную запись, чтобы повторный запуск
    # программы снова начинался с 400 + 400 часов.
    cursor.execute("""
        DELETE FROM workload_hours
        WHERE teacher_id = ?
          AND academic_year = ?
          AND work_type_id = ?
          AND record_type = 'План'
    """, (teacher_id, ACADEMIC_YEAR, work_type_id))

    # Добавляем 400 часов в первом и 400 часов во втором семестре.
    cursor.execute("""
        INSERT INTO workload_hours
            (teacher_id, academic_year, work_type_id, record_type,
             hours_sem1, hours_sem2, comment)
        VALUES (?, ?, ?, 'План', 400, 400, ?)
    """, (teacher_id, ACADEMIC_YEAR, work_type_id,
          "Тестовая запись: 400 часов в каждом семестре"))

    record_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return teacher_id, record_id


def main():
    # Создаём базу и добавляем тестовые данные.
    create_database()
    teacher_id, record_id = add_test_data()

    print("База данных создана.")

    # Первая проверка: 400 + 400 = 800 часов.
    result = check_teacher_workload(teacher_id, ACADEMIC_YEAR)

    if result["status"] == "success":
        print("Корректно:", result["message"])
    else:
        print("Ошибка:", result["message"])

    # Добавляем ещё 800 часов в первый семестр.
    # Итого получается 1200 + 400 = 1600 часов.
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("""
        UPDATE workload_hours
        SET hours_sem1 = hours_sem1 + 800
        WHERE record_id = ?
    """, (record_id,))
    conn.commit()
    conn.close()

    # Вторая проверка должна обнаружить превышение нормы.
    result = check_teacher_workload(teacher_id, ACADEMIC_YEAR)

    if result["status"] == "error":
        print("Ошибка:", result["message"])
    else:
        print("Корректно:", result["message"])


if __name__ == "__main__":
    main()
