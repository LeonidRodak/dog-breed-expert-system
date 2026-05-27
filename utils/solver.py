import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import sqlite3
from utils.db import get_db_connection

def check_property_match(breed_id: int, prop_id: int, user_value, conn):
    """Проверяет, соответствует ли значение пользователя значению для породы"""
    cur = conn.cursor()
    
    # Вещественное свойство
    cur.execute("""
        SELECT вм.мин_значение, вм.макс_значение 
        FROM описание_свойств_породы о
        JOIN вещественное_значение_для_породы вм ON вм.описание_id = о.идентификатор
        WHERE о.порода_id = ? AND о.свойство_id = ?
    """, (breed_id, prop_id))
    row = cur.fetchone()
    if row:
        min_val, max_val = row
        return min_val <= float(user_value) <= max_val, f"{min_val} - {max_val}"

    # Целое свойство
    cur.execute("""
        SELECT цм.мин_значение, цм.макс_значение 
        FROM описание_свойств_породы о
        JOIN целое_значение_для_породы цм ON цм.описание_id = о.идентификатор
        WHERE о.порода_id = ? AND о.свойство_id = ?
    """, (breed_id, prop_id))
    row = cur.fetchone()
    if row:
        min_val, max_val = row
        return min_val <= int(user_value) <= max_val, f"{min_val} - {max_val}"

    # Категориальное свойство
    cur.execute("""
        SELECT кзн.значение 
        FROM описание_свойств_породы о
        JOIN категориальное_значение_для_породы кз ON кз.описание_id = о.идентификатор
        JOIN категориальные_значения кзн ON кзн.идентификатор = кз.категориальное_значение_id
        WHERE о.порода_id = ? AND о.свойство_id = ?
    """, (breed_id, prop_id))
    allowed = [r[0] for r in cur.fetchall()]
    if allowed:
        match = str(user_value) in allowed
        return match, ", ".join(allowed)
    
    return False, "Нет данных"

def refute_hypotheses(user_input: dict):
    """
    Алгоритм опровержения гипотез (строго по разделу 3.5 документа)
    user_input = {'вес': 35.0, 'рост в холке': 60.0, 'тип шерсти': 'Средняя', ...}
    """
    if not user_input:
        return [], [], "Не введено ни одного свойства"

    conn = get_db_connection()
    cur = conn.cursor()

    # Получаем все породы
    cur.execute("SELECT идентификатор, название FROM породa_собаки")
    breeds = cur.fetchall()

    possible_breeds = []
    refuted = []  # список (порода, причина)

    for breed_id, breed_name in breeds:
        is_possible = True
        reasons = []

        # Проверяем каждое введённое пользователем свойство
        for prop_name, user_value in user_input.items():
            # Находим ID свойства
            cur.execute("SELECT идентификатор FROM свойство WHERE название = ?", (prop_name,))
            prop_row = cur.fetchone()
            if not prop_row:
                continue
            prop_id = prop_row[0]

            match, allowed_str = check_property_match(breed_id, prop_id, user_value, conn)
            
            if not match:
                is_possible = False
                reasons.append(f"Свойство «{prop_name}» = {user_value} не входит в {allowed_str}")
                break  # можно продолжить проверку остальных, но по алгоритму достаточно одной причины

        if is_possible:
            possible_breeds.append(breed_name)
        else:
            refuted.append((breed_name, "; ".join(reasons) or "Не соответствует введённым данным"))

    conn.close()

    # Формируем результат
    if len(possible_breeds) == 1:
        result = f"Порода: {possible_breeds[0]}"
        explanation = f"Подходящая порода: {possible_breeds[0]}"
    elif len(possible_breeds) > 1:
        result = f"Возможные породы: {', '.join(possible_breeds)}"
        explanation = f"Подходят несколько пород: {', '.join(possible_breeds)}"
    else:
        result = "Порода не определена"
        explanation = "Ни одна порода не соответствует введённым данным"

    return possible_breeds, refuted, explanation

# Тест при запуске файла
if __name__ == "__main__":
    # Пример из документа (раздел 2.3.2)
    test_input = {
        'вес': 35,
        'рост в холке': 60,
        'тип шерсти': 'Средняя',
        'темперамент': 'Активный',
        'продолжительность жизни': 12,
        'назначение': 'Служебная'
    }
    possible, refuted, expl = refute_hypotheses(test_input)
    print("✅ Тест решателя пройден")
    print("Результат:", possible)
    print("Опровергнуто:", len(refuted), "пород")