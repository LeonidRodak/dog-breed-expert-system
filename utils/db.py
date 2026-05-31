import sqlite3
import pandas as pd
import json

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
    """Показывает ТОЛЬКО активные свойства (фильтрация в Python — обходим баг pandas)"""
    print(f"🔍 get_breed_values для породы: {breed_name}")
    
    conn = get_db_connection()
    query = """
    SELECT 
        с.название as свойство,
        COALESCE(о.активно, 1) as активно,
        CASE 
            WHEN вм.мин_значение IS NOT NULL THEN вм.мин_значение || ' - ' || вм.макс_значение
            WHEN цм.мин_значение IS NOT NULL THEN цм.мин_значение || ' - ' || цм.макс_значение
            ELSE GROUP_CONCAT(кзн.значение, ', ')
        END as значение
    FROM породa_собаки п
    JOIN описание_свойств_породы о ON о.порода_id = п.идентификатор
    JOIN свойство с ON о.свойство_id = с.идентификатор
    LEFT JOIN вещественное_значение_для_породы вм ON вм.описание_id = о.идентификатор
    LEFT JOIN целое_значение_для_породы цм ON цм.описание_id = о.идентификатор
    LEFT JOIN категориальное_значение_для_породы кз ON кз.описание_id = о.идентификатор
    LEFT JOIN категориальные_значения кзн ON кзн.идентификатор = кз.категориальное_значение_id
    WHERE п.название = ?
    GROUP BY с.название, вм.мин_значение, цм.мин_значение, о.активно
    ORDER BY с.название
    """
    df = pd.read_sql_query(query, conn, params=(breed_name,))
    conn.close()
    
    # Фильтруем активные свойства уже в Python (это обходит проблему SQLite + pandas)
    if 'активно' in df.columns:
        df = df[df['активно'] == 1].copy()
    
    def clean_value(val):
        if pd.isna(val):
            return val
        items = str(val).split(', ')
        return ', '.join(sorted(set(items)))
    
    if not df.empty:
        df['значение'] = df['значение'].apply(clean_value)
        df = df.drop(columns=['активно'], errors='ignore')
    
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
    """Добавляет новое свойство. Запрещает дубликаты БЕЗ УЧЁТА РЕГИСТРА (работает с кириллицей)."""
    if not name or not name.strip():
        return False
    
    name_clean = name.strip()
    name_lower = name_clean.lower()
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Проверяем через Python — 100% надёжно для кириллицы
        cur.execute("SELECT название FROM свойство")
        existing = [row[0].lower() for row in cur.fetchall()]
        
        if name_lower in existing:
            return False  # уже существует (игнорируя регистр)
        
        cur.execute("INSERT INTO свойство (название) VALUES (?)", (name_clean,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_property(name: str):
    """Мягкое удаление: удаляем ТОЛЬКО название свойства.
    Все данные (типы, диапазоны, категориальные значения, значения для пород) остаются в базе."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM свойство WHERE название = ?", (name,))
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    finally:
        conn.close()

def reset_properties_to_default():
    """Полное восстановление исходных 6 свойств + всех типов + глобальных диапазонов + 
    категориальных значений + связей. 
    Используем оригинальный populate_database — он сделан именно для этого и 
    использует INSERT OR IGNORE везде, поэтому значения пород НЕ удаляются."""
    from database.populate_data import populate_database
    
    populate_database()
    return True


def get_properties_for_breed(breed_name: str):
    """Возвращает свойства + их активность для чекбоксов"""
    conn = get_db_connection()
    query = """
    SELECT 
        с.название, 
        COALESCE(о.активно, 1) as активно
    FROM свойство с
    LEFT JOIN описание_свойств_породы о 
        ON о.свойство_id = с.идентификатор 
       AND о.порода_id = (SELECT идентификатор FROM породa_собаки WHERE название = ?)
    ORDER BY с.название
    """
    df = pd.read_sql_query(query, conn, params=(breed_name,))
    conn.close()
    df['selected'] = df['активно'].astype(int)
    return df.drop(columns=['активно'], errors='ignore')


def update_breed_properties(breed_name: str, selected_properties: list):
    """Управляет видимостью свойств через флаг 'активно'.
    Теперь вместо DELETE/INSERT просто меняем флаг — значения никогда не теряются."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Получаем ID породы
        cur.execute("SELECT идентификатор FROM породa_собаки WHERE название = ?", (breed_name,))
        breed_id_row = cur.fetchone()
        if not breed_id_row:
            return False
        breed_id = breed_id_row[0]

        # ID выбранных свойств
        selected_ids = set()
        for name in selected_properties:
            cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (name,))
            row = cur.fetchone()
            if row:
                selected_ids.add(row[0])

        # 1. Все свойства, которые должны быть активны — ставим активно = 1 (или создаём запись)
        for pid in selected_ids:
            cur.execute("""
                INSERT OR IGNORE INTO описание_свойств_породы 
                (порода_id, свойство_id, активно) 
                VALUES (?, ?, 1)
            """, (breed_id, pid))
            
            cur.execute("""
                UPDATE описание_свойств_породы 
                SET активно = 1 
                WHERE порода_id = ? AND свойство_id = ?
            """, (breed_id, pid))

        # 2. Свойства, которые сняты — ставим активно = 0
        cur.execute("""
            UPDATE описание_свойств_породы 
            SET активно = 0 
            WHERE порода_id = ? 
              AND свойство_id NOT IN (SELECT value FROM json_each(?))
        """, (breed_id, json.dumps(list(selected_ids))))

        conn.commit()
        print(f"update_breed_properties: обновлена видимость свойств для '{breed_name}'")
        return True
    except Exception as e:
        print(f"Ошибка в update_breed_properties: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

        

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
    """Возвращает значение свойства (используется в редакторе значений).
    Теперь проверяем активно = 1, но если нужно редактировать даже скрытые свойства — 
    можно убрать условие о.активно = 1 (оставил как есть, чтобы соответствовало просмотру)."""
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
                WHERE EXISTS (
                    SELECT 1 
                    FROM описание_свойств_породы o 
                    WHERE o.идентификатор = v.описание_id 
                      AND o.порода_id = ? 
                      AND o.свойство_id = ?
                      AND o.активно = 1
                )
            """, (breed_id, prop_id))
            row = cur.fetchone()
            if row:
                return {'type': 'numeric' if prop_type == "вещественное" else 'integer', 'min': row[0], 'max': row[1]}
            return None

        else:  # категориальное
            cur.execute("""
                SELECT DISTINCT кзн.значение
                FROM категориальное_значение_для_породы кз
                JOIN описание_свойств_породы o ON кз.описание_id = o.идентификатор
                JOIN категориальные_значения кзн ON кз.категориальное_значение_id = кзн.идентификатор
                WHERE o.порода_id = ? 
                  AND o.свойство_id = ?
                  AND o.активно = 1
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



def check_numeric_conflicts(prop_name: str, new_min, new_max):
    """Проверяет, есть ли породы, значения которых выходят за новый глобальный диапазон."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Определяем таблицу по типу свойства
    if prop_name.lower() in ["вес", "рост в холке"]:
        table = "вещественное_значение_для_породы"
    else:
        table = "целое_значение_для_породы"
    
    cur.execute(f"""
        SELECT DISTINCT п.название, вм.мин_значение, вм.макс_значение
        FROM {table} вм
        JOIN описание_свойств_породы о ON вм.описание_id = о.идентификатор
        JOIN породa_собаки п ON о.порода_id = п.идентификатор
        JOIN свойство с ON о.свойство_id = с.идентификатор
        WHERE с.название = ?
          AND (вм.мин_значение < ? OR вм.макс_значение > ?)
        ORDER BY п.название
    """, (prop_name, new_min, new_max))
    
    conflicts = cur.fetchall()
    conn.close()
    return conflicts


def trim_breed_numeric_values(prop_name: str, new_min, new_max):
    """Финальная версия обрезки.
    Гарантирует, что диапазон породы всегда лежит внутри глобального диапазона (min <= max)."""
    print(f"🔧 Финальная обрезка для '{prop_name}' -> {new_min} - {new_max}")
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if prop_name.lower() in ["вес", "рост в холке"]:
            table = "вещественное_значение_для_породы"
        else:
            table = "целое_значение_для_породы"
        
        # Прямая обрезка
        cur.execute(f"""
            UPDATE {table}
            SET мин_значение = MAX(мин_значение, ?),
                макс_значение = MIN(макс_значение, ?)
            WHERE описание_id IN (
                SELECT о.идентификатор 
                FROM описание_свойств_породы о
                JOIN свойство с ON о.свойство_id = с.идентификатор
                WHERE с.название = ?
            )
        """, (float(new_min), float(new_max), prop_name))
        
        # Дополнительная защита: если после обрезки min > max — приводим диапазон породы полностью к глобальному
        cur.execute(f"""
            UPDATE {table}
            SET мин_значение = ?,
                макс_значение = ?
            WHERE описание_id IN (
                SELECT о.идентификатор 
                FROM описание_свойств_породы о
                JOIN свойство с ON о.свойство_id = с.идентификатор
                WHERE с.название = ?
            )
            AND мин_значение > макс_значение
        """, (float(new_min), float(new_max), prop_name))
        
        updated = cur.rowcount
        conn.commit()
        print(f"✅ Финальная обрезка завершена. Обновлено {updated} записей для '{prop_name}'")
        return updated > 0
    except Exception as e:
        print(f"❌ Ошибка финальной обрезки: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def check_categorical_conflicts(prop_name: str, new_values: list):
    """Проверяет, есть ли породы, которые используют удаляемые категориальные значения."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT DISTINCT п.название, кзн.значение
        FROM категориальное_значение_для_породы кз
        JOIN описание_свойств_породы о ON кз.описание_id = о.идентификатор
        JOIN породa_собаки п ON о.порода_id = п.идентификатор
        JOIN категориальные_значения кзн ON кз.категориальное_значение_id = кзн.идентификатор
        JOIN свойство с ON о.свойство_id = с.идентификатор
        WHERE с.название = ?
          AND кзн.значение NOT IN ({})
    """.format(','.join(['?'] * len(new_values))), [prop_name] + new_values)
    
    conflicts = cur.fetchall()
    conn.close()
    return conflicts


def trim_breed_categorical_values(prop_name: str, new_values: list):
    """Удаляет из пород те категориальные значения, которых больше нет в глобальном списке."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        DELETE FROM категориальное_значение_для_породы
        WHERE описание_id IN (
            SELECT о.идентификатор
            FROM описание_свойств_породы о
            JOIN свойство с ON о.свойство_id = с.идентификатор
            WHERE с.название = ?
        )
        AND категориальное_значение_id IN (
            SELECT кзн.идентификатор
            FROM категориальные_значения кзн
            JOIN категориальные_свойства кс ON кзн.категориальное_свойство_id = кс.идентификатор
            JOIN свойство с ON кс.свойство_id = с.идентификатор
            WHERE с.название = ?
              AND кзн.значение NOT IN ({})
        )
    """.format(','.join(['?'] * len(new_values))), [prop_name, prop_name] + new_values)
    
    conn.commit()
    conn.close()        


def reset_possible_values_to_default():
    """Полный сброс: очищает все значения пород и глобальные диапазоны,
    затем заново заполняет базу из populate_database()."""
    print("=== ПОЛНЫЙ СБРОС ВОЗМОЖНЫХ ЗНАЧЕНИЙ ===")
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. Очищаем все значения пород (чтобы старые обрезанные значения удалились)
        cur.execute("DELETE FROM вещественное_значение_для_породы")
        cur.execute("DELETE FROM целое_значение_для_породы")
        cur.execute("DELETE FROM категориальное_значение_для_породы")
        
        # 2. Очищаем глобальные диапазоны
        cur.execute("DELETE FROM вещественные_свойства")
        cur.execute("DELETE FROM целые_свойства")
        cur.execute("DELETE FROM категориальные_свойства")
        cur.execute("DELETE FROM категориальные_значения")
        
        conn.commit()
        print("✅ Таблицы значений очищены")
        
        # 3. Заполняем всё заново из исходных данных курсовой
        from database.populate_data import populate_database
        populate_database()
        
        print("✅ Полный сброс выполнен успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()




def update_breed_properties_global():
    """Глобальное восстановление ВСЕХ свойств у ВСЕХ пород собак.
    Использует populate_database(), поэтому значения тоже возвращаются."""
    from database.populate_data import populate_database
    populate_database()
    print("✅ Глобальное восстановление всех свойств для всех пород выполнено")
    return True

print("✅ Модуль db.py готов")
