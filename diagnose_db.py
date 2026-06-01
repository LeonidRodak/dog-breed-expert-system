import sqlite3
import os

DB_PATH = "database/knowledge_base.db"
FULL_PATH = os.path.abspath(DB_PATH)

print(" ДИАГНОСТИКА БАЗЫ ДАННЫХ")
print(f"Текущая папка: {os.getcwd()}")
print(f"Путь к БД, которую использует приложение: {FULL_PATH}\n")

if not os.path.exists(FULL_PATH):
    print(" База данных НЕ НАЙДЕНА по этому пути!")
    exit(1)

conn = sqlite3.connect(FULL_PATH)
cur = conn.cursor()

# Показываем структуру таблицы
print(" Структура таблицы 'описание_свойств_породы':")
cur.execute("PRAGMA table_info(описание_свойств_породы)")
columns = cur.fetchall()
for col in columns:
    print(col)

# Проверяем наличие колонки активно
has_active = any(col[1] == "активно" for col in columns)

if has_active:
    print("\n Колонка 'активно' найдена")
else:
    print("\n Колонки 'активно' нет — добавляем...")
    cur.execute("""
        ALTER TABLE описание_свойств_породы 
        ADD COLUMN активно BOOLEAN DEFAULT 1 NOT NULL CHECK (активно IN (0, 1))
    """)
    print(" Колонка 'активно' успешно добавлена!")

# Делаем все записи активными
cur.execute("UPDATE описание_свойств_породы SET активно = 1 WHERE активно IS NULL")
print(f" Обновлено записей: {cur.rowcount}")

conn.commit()
conn.close()

print("\n ДИАГНОСТИКА И ИСПРАВЛЕНИЕ ЗАВЕРШЕНЫ!")
print("Теперь:")
print("1. Полностью закрой Streamlit (Ctrl+C)")
print("2. Запусти: streamlit run app.py")
print("3. После запуска верни в utils/db.py полную версию get_breed_values с 'o.активно = 1'")