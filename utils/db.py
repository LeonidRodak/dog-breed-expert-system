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


def get_property_type(prop_name: str) -> str:
    """Определяет тип свойства (вещественное / целое / категориальное)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Проверяем вещественные свойства
        cur.execute("""
            SELECT 1 
            FROM вещественные_свойства vs 
            JOIN свойство с ON vs.свойство_id = с.идентификатор 
            WHERE с.название = ?
        """, (prop_name,))
        if cur.fetchone():
            return "вещественное"
        
        # Проверяем целые свойства
        cur.execute("""
            SELECT 1 
            FROM целые_свойства цс 
            JOIN свойство с ON цс.свойство_id = с.идентификатор 
            WHERE с.название = ?
        """, (prop_name,))
        if cur.fetchone():
            return "целое"
        
        # Проверяем категориальные свойства
        cur.execute("""
            SELECT 1 
            FROM категориальные_свойства кс 
            JOIN свойство с ON кс.свойство_id = с.идентификатор 
            WHERE с.название = ?
        """, (prop_name,))
        if cur.fetchone():
            return "категориальное"
        
        return "неизвестно"
    
    finally:
        # Гарантированно закрываем соединение в любом случае
        conn.close()


def get_global_numeric_range(prop_name: str):
    """Возвращает глобальный диапазон для вещественного/целого свойства"""
    conn = get_db_connection()
    query = """
        SELECT мин_значение_глобальное as min, макс_значение_глобальное as max
        FROM вещественные_свойства vs
        JOIN свойство с ON vs.свойство_id = с.идентификатор
        WHERE с.название = ?
        UNION
        SELECT мин_значение_глобальное as min, макс_значение_глобальное as max
        FROM целые_свойства цс
        JOIN свойство с ON цс.свойство_id = с.идентификатор
        WHERE с.название = ?
    """
    df = pd.read_sql_query(query, conn, params=(prop_name, prop_name))
    conn.close()
    return df.iloc[0].to_dict() if not df.empty else None


def save_global_numeric_range(prop_name: str, min_val, max_val):
    """Сохраняет/обновляет глобальный диапазон"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Находим id свойства
    cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
    prop_id = cur.fetchone()[0]
    
    # Проверяем тип и обновляем
    cur.execute("SELECT 1 FROM вещественные_свойства WHERE свойство_id = ?", (prop_id,))
    if cur.fetchone():
        cur.execute("""
            UPDATE вещественные_свойства 
            SET мин_значение_глобальное = ?, макс_значение_глобальное = ?
            WHERE свойство_id = ?
        """, (min_val, max_val, prop_id))
    else:
        cur.execute("""
            UPDATE целые_свойства 
            SET мин_значение_глобальное = ?, макс_значение_глобальное = ?
            WHERE свойство_id = ?
        """, (int(min_val), int(max_val), prop_id))
    
    conn.commit()
    conn.close()


def get_categorical_values(prop_name: str):
    """Возвращает список категориальных значений БЕЗ дубликатов"""
    conn = get_db_connection()
    query = """
        SELECT DISTINCT кзн.значение
        FROM категориальные_значения кзн
        JOIN категориальные_свойства кс ON кзн.категориальное_свойство_id = кс.идентификатор
        JOIN свойство с ON кс.свойство_id = с.идентификатор
        WHERE с.название = ?
        ORDER BY кзн.значение
    """
    df = pd.read_sql_query(query, conn, params=(prop_name,))
    conn.close()
    return df['значение'].tolist() if not df.empty else []


def add_categorical_value(prop_name: str, value: str):
    """Добавляет значение с защитой от дубликатов"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Получаем id свойства
    cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
    prop_id = cur.fetchone()[0]
    
    # Получаем id категориального свойства
    cur.execute("SELECT идентификатор FROM категориальные_свойства WHERE свойство_id = ?", (prop_id,))
    cat_prop_id = cur.fetchone()[0]
    
    # Добавляем только если такого значения ещё нет
    cur.execute("""
        INSERT OR IGNORE 
        INTO категориальные_значения (категориальное_свойство_id, значение)
        VALUES (?, ?)
    """, (cat_prop_id, value))
    
    conn.commit()
    conn.close()


def delete_categorical_value(prop_name: str, value: str):
    """Удаляет категориальное значение"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        DELETE FROM категориальные_значения 
        WHERE значение = ? 
        AND категориальное_свойство_id = (
            SELECT кс.идентификатор 
            FROM категориальные_свойства кс 
            JOIN свойство с ON кс.свойство_id = с.идентификатор 
            WHERE с.название = ?
        )
    """, (value, prop_name))
    
    conn.commit()
    conn.close()


def get_breed_specific_value(breed_name: str, prop_name: str):
    """Возвращает значение свойства для конкретной породы (без дубликатов)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT идентификатор FROM породa_собаки WHERE название = ?", (breed_name,))
        breed_id_row = cur.fetchone()
        if not breed_id_row:
            return None
        breed_id = breed_id_row[0]

        cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
        prop_id_row = cur.fetchone()
        if not prop_id_row:
            return None
        prop_id = prop_id_row[0]

        prop_type = get_property_type(prop_name)

        if prop_type in ["вещественное", "целое"]:
            table = "вещественное_значение_для_породы" if prop_type == "вещественное" else "целое_значение_для_породы"
            cur.execute(f"""
                SELECT мин_значение as min, макс_значение as max
                FROM {table} v
                JOIN описание_свойств_породы о ON v.описание_id = о.идентификатор
                WHERE о.порода_id = ? AND о.свойство_id = ?
            """, (breed_id, prop_id))
            row = cur.fetchone()
            if row:
                return {'type': 'numeric' if prop_type == "вещественное" else 'integer', 'min': row[0], 'max': row[1]}
            return None

        else:  # категориальное
            cur.execute("""
                SELECT DISTINCT кзн.значение
                FROM категориальное_значение_для_породы кз
                JOIN описание_свойств_породы о ON кз.описание_id = о.идентификатор
                JOIN категориальные_значения кзн ON кз.категориальное_значение_id = кзн.идентификатор
                WHERE о.порода_id = ? AND о.свойство_id = ?
                ORDER BY кзн.значение
            """, (breed_id, prop_id))
            values = [row[0] for row in cur.fetchall()]
            return {'type': 'categorical', 'values': values} if values else None

    finally:
        conn.close()


def save_breed_numeric_value(breed_name: str, prop_name: str, min_val, max_val):
    """Сохраняет диапазон для числового/целого свойства породы"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Получаем id породы и свойства
    cur.execute("SELECT идентификатор FROM породa_собаки WHERE название = ?", (breed_name,))
    breed_id = cur.fetchone()[0]
    cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
    prop_id = cur.fetchone()[0]
    
    # Убеждаемся, что связь в описание_свойств_породы существует
    cur.execute("INSERT OR IGNORE INTO описание_свойств_породы (порода_id, свойство_id) VALUES (?, ?)", 
                (breed_id, prop_id))
    cur.execute("SELECT идентификатор FROM описание_свойств_породы WHERE порода_id = ? AND свойство_id = ?", 
                (breed_id, prop_id))
    desc_id = cur.fetchone()[0]
    
    # Определяем тип свойства
    if "вес" in prop_name.lower() or "рост" in prop_name.lower():
        table = "вещественное_значение_для_породы"
    else:
        table = "целое_значение_для_породы"
    
    cur.execute(f"INSERT OR REPLACE INTO {table} (описание_id, мин_значение, макс_значение) VALUES (?, ?, ?)",
                (desc_id, min_val, max_val))
    
    conn.commit()
    conn.close()


def save_breed_categorical_values(breed_name: str, prop_name: str, selected_values: list):
    """Сохраняет категориальные значения для породы БЕЗ дубликатов"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Получаем id породы и свойства
        cur.execute("SELECT идентификатор FROM породa_собаки WHERE название = ?", (breed_name,))
        breed_id = cur.fetchone()[0]
        
        cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
        prop_id = cur.fetchone()[0]

        # Убеждаемся, что запись в описание_свойств_породы существует
        cur.execute("""
            INSERT OR IGNORE INTO описание_свойств_породы (порода_id, свойство_id) 
            VALUES (?, ?)
        """, (breed_id, prop_id))
        
        cur.execute("""
            SELECT идентификатор FROM описание_свойств_породы 
            WHERE порода_id = ? AND свойство_id = ?
        """, (breed_id, prop_id))
        desc_id = cur.fetchone()[0]

        # Удаляем старые значения
        cur.execute("DELETE FROM категориальное_значение_для_породы WHERE описание_id = ?", (desc_id,))

        # Добавляем новые значения (защита от дубликатов)
        for val in selected_values:
            cur.execute("""
                INSERT OR IGNORE INTO категориальное_значение_для_породы (описание_id, категориальное_значение_id)
                SELECT ?, идентификатор 
                FROM категориальные_значения 
                WHERE значение = ? 
                  AND категориальное_свойство_id = (
                      SELECT идентификатор 
                      FROM категориальные_свойства 
                      WHERE свойство_id = ?
                  )
            """, (desc_id, val, prop_id))
        
        conn.commit()
        # УСПЕХ ВЫВОДИМ В app.py, а не здесь!
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"Ошибка сохранения: {e}")
        return False
    finally:
        conn.close()


print("✅ Модуль db.py готов")
