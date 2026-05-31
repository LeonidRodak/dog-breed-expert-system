import sqlite3
import os

DB_PATH = "database/knowledge_base.db"

print("🔍 Диагностика...")
if not os.path.exists(DB_PATH):
    print(f"❌ База не найдена: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Проверяем структуру таблицы
cur.execute("PRAGMA table_info(описание_свойств_породы)")
columns = [col[1] for col in cur.fetchall()]

if "активно" in columns:
    print("✅ Колонка 'активно' уже существует")
else:
    print("➕ Добавляем колонку 'активно'...")
    cur.execute("""
        ALTER TABLE описание_свойств_породы 
        ADD COLUMN активно BOOLEAN DEFAULT 1 NOT NULL CHECK (активно IN (0, 1))
    """)
    print("✅ Колонка добавлена!")

# Делаем все существующие свойства активными
cur.execute("UPDATE описание_свойств_породы SET активно = 1 WHERE активно IS NULL")
print(f"✅ Обновлено записей: {cur.rowcount}")

conn.commit()
conn.close()
print("\n🎉 МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
print("Теперь перезапусти приложение:")
print("   streamlit run app.py")