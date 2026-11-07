
import sqlite3

DB_NAME = "university_reports_demo.db"

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS departments (
    department_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_name TEXT NOT NULL,
    institute TEXT NOT NULL DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (department_name, institute)
);

CREATE TABLE IF NOT EXISTS positions (
    position_id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_name TEXT NOT NULL UNIQUE,
    max_teaching_hours REAL NOT NULL DEFAULT 800,
    annual_full_time_hours REAL NOT NULL DEFAULT 1524
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

CREATE TABLE IF NOT EXISTS teachers (
    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER NOT NULL,
    position_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    birth_date TEXT,
    degree TEXT,
    academic_title TEXT,
    rate REAL NOT NULL DEFAULT 1,
    years_in_university INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (position_id) REFERENCES positions(position_id)
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
    group_code TEXT NOT NULL DEFAULT '',
    student_count INTEGER DEFAULT 0,
    semester INTEGER NOT NULL,
    lecture_hours REAL DEFAULT 0,
    practice_hours REAL DEFAULT 0,
    laboratory_hours REAL DEFAULT 0,
    consultation_hours REAL DEFAULT 0,
    exam_hours REAL DEFAULT 0,
    coursework_hours REAL DEFAULT 0,
    thesis_hours REAL DEFAULT 0,
    other_hours REAL DEFAULT 0,
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


def get_connection():
    """Открывает подключение к базе данных."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_database():
    """Создаёт базу и таблицы, если их ещё нет."""
    conn = get_connection()
    try:
        conn.executescript(CREATE_TABLES)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    create_database()
    print("База данных и 10 таблиц успешно созданы.")
