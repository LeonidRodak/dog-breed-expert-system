import sqlite3
import pandas as pd

def get_db_connection():
    """Подключение к базе знаний"""
    return sqlite3.connect('database/knowledge_base.db', check_same_thread=False)

def get_all_properties():
    """Возвращает все свойства"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM свойство", conn)
    conn.close()
    return df

def get_all_breeds():
    """Возвращает все породы"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM породa_собаки ORDER BY название", conn)
    conn.close()
    return df

def get_breed_values(breed_name: str):
    """Показывает значения свойств. 
    Значения НЕ теряются при отключении свойства в 'Описание свойств вида'."""
    conn = get_db_connection()
    query = """
    SELECT 
        с.название as свойство,
        CASE 
            WHEN вм.мин_значение IS NOT NULL THEN вм.мин_значение || ' - ' || вм.макс_значение
            WHEN цм.мин_значение IS NOT NULL THEN цм.мин_значение || ' - ' || цм.макс_значение
            ELSE GROUP_CONCAT(кзн.значение, ', ')
        END as значение
    FROM породa_собаки п
    CROSS JOIN свойство с
    LEFT JOIN описание_свойств_породы о 
        ON о.порода_id = п.идентификатор 
       AND о.свойство_id = с.идентификатор
    LEFT JOIN вещественное_значение_для_породы вм ON вм.описание_id = о.идентификатор
    LEFT JOIN целое_значение_для_породы цм ON цм.описание_id = о.идентификатор
    LEFT JOIN категориальное_значение_для_породы кз ON кз.описание_id = о.идентификатор
    LEFT JOIN категориальные_значения кзн ON кзн.идентификатор = кз.категориальное_значение_id
    WHERE п.название = ?
    GROUP BY с.название, вм.мин_значение, цм.мин_значение
    ORDER BY с.название
    """
    df = pd.read_sql_query(query, conn, params=(breed_name,))
    conn.close()
    
    # Убираем дубликаты в категориальных значениях через pandas
    def clean_value(val):
        if pd.isna(val):
            return val
        items = str(val).split(', ')
        return ', '.join(sorted(set(items)))
    
    df['значение'] = df['значение'].apply(clean_value)
    return df

def get_breeds_for_editor():
    """Возвращает только названия пород для редактирования (без ID)"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT название FROM породa_собаки ORDER BY название", conn)
    conn.close()
    return df

def add_breed(name: str):
    """Добавляет новую породу"""
    if not name or not name.strip():
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO породa_собаки (название) VALUES (?)", (name.strip(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # уже существует
    finally:
        conn.close()

def delete_breed(name: str):
    """Удаляет породу по названию"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM породa_собаки WHERE название = ?", (name,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def check_knowledge_completeness():
    """Проверка полноты знаний (как в документе)"""
    conn = get_db_connection()
    cur = conn.cursor()
    errors = []
    
    cur.execute("SELECT COUNT(*) FROM породa_собаки")
    if cur.fetchone()[0] == 0:
        errors.append("Нет ни одной породы собак")
    
    cur.execute("SELECT COUNT(*) FROM свойство")
    if cur.fetchone()[0] == 0:
        errors.append("Нет ни одного свойства")
    
    cur.execute("SELECT COUNT(*) FROM описание_свойств_породы")
    if cur.fetchone()[0] == 0:
        errors.append("Нет описаний свойств для пород")
    
    conn.close()
    return errors if errors else ["✅ Все данные заполнены корректно!"]

def reset_breeds_to_default():
    """Полностью восстанавливает исходные 20 пород собак из лабораторной"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM породa_собаки")
    conn.commit()
    conn.close()
    
    # Вызываем заполнение исходными данными
    from database.populate_data import populate_database
    populate_database()
    return True

def reset_breeds_to_default_safe():
    """Добавляет недостающие исходные 20 пород, не удаляя пользовательские"""
    from database.populate_data import populate_database
    # populate_database уже использует INSERT OR IGNORE, поэтому безопасно
    populate_database()
    return True

def get_properties_for_editor():
    """Возвращает только названия свойств для редактирования"""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT название FROM свойство ORDER BY название", conn)
    conn.close()
    return df

def add_property(name: str):
    """Добавляет новое свойство"""
    if not name or not name.strip():
        return False
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO свойство (название) VALUES (?)", (name.strip(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # уже существует
    finally:
        conn.close()

def delete_property(name: str):
    """Удаляет свойство по названию"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM свойство WHERE название = ?", (name,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def reset_properties_to_default():
    """Восстанавливает только исходные 6 свойств, НЕ удаляя добавленные пользователем"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Добавляем только те свойства, которых ещё нет (OR IGNORE)
    default_properties = [
        ('вес',),
        ('рост в холке',),
        ('тип шерсти',),
        ('темперамент',),
        ('продолжительность жизни',),
        ('назначение',)
    ]
    cur.executemany("INSERT OR IGNORE INTO свойство (название) VALUES (?)", default_properties)
    
    conn.commit()
    conn.close()
    return True


def get_properties_for_breed(breed_name: str):
    """Возвращает список свойств и какие из них назначены породе"""
    conn = get_db_connection()
    query = """
    SELECT с.название, 
           CASE WHEN о.порода_id IS NOT NULL THEN 1 ELSE 0 END as selected
    FROM свойство с
    LEFT JOIN описание_свойств_породы о 
        ON о.свойство_id = с.идентификатор 
       AND о.порода_id = (SELECT идентификатор FROM породa_собаки WHERE название = ?)
    ORDER BY с.название
    """
    df = pd.read_sql_query(query, conn, params=(breed_name,))
    conn.close()
    return df

def update_breed_properties(breed_name: str, selected_properties: list):
    """Только управляет видимостью свойств. 
    Никогда не удаляет сами значения (диапазоны и списки)."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # ID породы
    cur.execute("SELECT идентификатор FROM породa_собаки WHERE название = ?", (breed_name,))
    breed_id = cur.fetchone()[0]
    
    # Текущие активные свойства
    cur.execute("SELECT свойство_id FROM описание_свойств_породы WHERE порода_id = ?", (breed_id,))
    current_ids = {row[0] for row in cur.fetchall()}
    
    # ID выбранных свойств
    selected_ids = set()
    for name in selected_properties:
        cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (name,))
        row = cur.fetchone()
        if row:
            selected_ids.add(row[0])
    
    # Удаляем только отключённые свойства (связь), значения остаются
    for pid in current_ids - selected_ids:
        cur.execute("DELETE FROM описание_свойств_породы WHERE порода_id = ? AND свойство_id = ?", 
                    (breed_id, pid))
    
    # Добавляем включённые свойства
    for pid in selected_ids - current_ids:
        cur.execute("INSERT OR IGNORE INTO описание_свойств_породы (порода_id, свойство_id) VALUES (?, ?)", 
                    (breed_id, pid))
    
    conn.commit()
    conn.close()
    return True

print("✅ Модуль db.py готов")