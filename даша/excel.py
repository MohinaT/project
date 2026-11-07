
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from database import get_connection


SHEETS = {
    "Кафедры": (
        "departments",
        ["Код кафедры", "Название кафедры", "Институт", "Дата создания"],
        ["department_id", "department_name", "institute", "created_at"]
    ),
    "Должности": (
        "positions",
        ["Код должности", "Название должности",
         "Предельная учебная нагрузка, ч",
         "Годовой объём на полную ставку, ч"],
        ["position_id", "position_name",
         "max_teaching_hours", "annual_full_time_hours"]
    ),
    "Пользователи": (
        "users",
        ["Логин", "Хэш пароля", "Роль",
         "Код преподавателя", "Код кафедры", "Активен"],
        ["login", "password_hash", "role",
         "teacher_id", "department_id", "is_active"]
    ),
    "Преподаватели": (
        "teachers",
        ["Код преподавателя", "Код кафедры", "Код должности",
         "ФИО", "Дата рождения", "Учёная степень",
         "Учёное звание", "Доля ставки",
         "Стаж в вузе, лет", "Активен"],
        ["teacher_id", "department_id", "position_id",
         "full_name", "birth_date", "degree",
         "academic_title", "rate",
         "years_in_university", "is_active"]
    ),
    "Учебные годы": (
        "academic_years",
        ["Название года", "Закрыт"],
        ["academic_year", "is_closed"]
    ),
    "Виды работ": (
        "work_types",
        ["Код вида работ", "Раздел", "Название вида работ",
         "Единица измерения", "Используется норма"],
        ["work_type_id", "section", "work_name", "unit", "uses_norm"]
    ),
    "Нормы времени": (
        "time_norms",
        ["Код нормы", "Код вида работ", "Код должности",
         "Значение нормы", "За что норма", "Дата начала",
         "Документ-основание"],
        ["norm_id", "work_type_id", "position_id",
         "norm_value", "norm_basis", "effective_from",
         "source_document"]
    ),
    "Учебное поручение": (
        "teaching_assignments",
        ["Код строки", "Код преподавателя", "Учебный год",
         "Дисциплина", "Группа", "Число студентов",
         "Семестр", "Часы лекций", "Часы практик",
         "Часы лабораторных", "Часы консультаций",
         "Часы экзамена", "Часы курсовых", "Часы ВКР",
         "Другие часы", "Итого часов"],
        ["assignment_id", "teacher_id", "academic_year",
         "discipline", "group_code", "student_count",
         "semester", "lecture_hours", "practice_hours",
         "laboratory_hours", "consultation_hours",
         "exam_hours", "coursework_hours", "thesis_hours",
         "other_hours", "total_hours"]
    ),
    "Часы план-факт": (
        "workload_hours",
        ["Код записи", "Код преподавателя", "Учебный год",
         "Код вида работ", "Тип", "Часы I семестр",
         "Часы II семестр", "Часы за год", "Комментарий"],
        ["record_id", "teacher_id", "academic_year",
         "work_type_id", "record_type", "hours_sem1",
         "hours_sem2", None, "comment"]
    ),
    "Документы": (
        "documents",
        ["Код документа", "Код преподавателя", "Учебный год",
         "Тип документа", "Путь к файлу",
         "Дата формирования", "Статус"],
        ["document_id", "teacher_id", "academic_year",
         "document_type", "file_path", "formatted_at", "status"]
    )
}


def create_excel(records=None):
    """Создаёт Excel-файл со всеми десятью таблицами базы."""
    conn = get_connection()

    try:
        workbook = Workbook()
        default_sheet = workbook.active
        workbook.remove(default_sheet)

        for sheet_name, settings in SHEETS.items():
            table_name, headers, fields = settings
            sheet = workbook.create_sheet(sheet_name)

            sheet.append(headers)

            if table_name == "workload_hours":
                rows = conn.execute(
                    "SELECT * FROM workload_hours ORDER BY record_id"
                ).fetchall()

                for row in rows:
                    values = []
                    for field in fields:
                        if field is None:
                            values.append(
                                row["hours_sem1"] + row["hours_sem2"]
                            )
                        else:
                            values.append(row[field])
                    sheet.append(values)
            else:
                rows = conn.execute(
                    f"SELECT * FROM {table_name}"
                ).fetchall()

                for row in rows:
                    sheet.append([row[field] for field in fields])

            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(
                    "solid", fgColor="315F9B"
                )
                cell.alignment = Alignment(
                    horizontal="center", vertical="center"
                )

            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions

            for column in sheet.columns:
                max_length = 0
                column_letter = column[0].column_letter

                for cell in column:
                    if cell.value is not None:
                        max_length = max(
                            max_length, len(str(cell.value))
                        )

                sheet.column_dimensions[column_letter].width = min(
                    max_length + 3, 35
                )

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        return output

    finally:
        conn.close()
