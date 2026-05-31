import sqlite3

def init_database():
    conn = sqlite3.connect('database/knowledge_base.db')
    cur = conn.cursor()
    
    cur.executescript('''
    DROP TABLE IF EXISTS породa_собаки;
    DROP TABLE IF EXISTS свойство;
    DROP TABLE IF EXISTS вещественные_свойства;
    DROP TABLE IF EXISTS целые_свойства;
    DROP TABLE IF EXISTS категориальные_свойства;
    DROP TABLE IF EXISTS категориальные_значения;
    DROP TABLE IF EXISTS описание_свойств_породы;
    DROP TABLE IF EXISTS вещественное_значение_для_породы;
    DROP TABLE IF EXISTS целое_значение_для_породы;
    DROP TABLE IF EXISTS категориальное_значение_для_породы;

    CREATE TABLE породa_собаки (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        название TEXT UNIQUE NOT NULL
    );

    CREATE TABLE свойство (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        название TEXT UNIQUE NOT NULL
    );

    CREATE TABLE вещественные_свойства (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        свойство_id INTEGER UNIQUE NOT NULL,
        мин_значение_глобальное REAL NOT NULL,
        макс_значение_глобальное REAL NOT NULL,
        FOREIGN KEY (свойство_id) REFERENCES свойство(идентификатор)
    );

    CREATE TABLE целые_свойства (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        свойство_id INTEGER UNIQUE NOT NULL,
        мин_значение_глобальное INTEGER NOT NULL,
        макс_значение_глобальное INTEGER NOT NULL,
        FOREIGN KEY (свойство_id) REFERENCES свойство(идентификатор)
    );

    CREATE TABLE категориальные_свойства (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        свойство_id INTEGER UNIQUE NOT NULL,
        FOREIGN KEY (свойство_id) REFERENCES свойство(идентификатор)
    );

    CREATE TABLE категориальные_значения (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        категориальное_свойство_id INTEGER NOT NULL,
        значение TEXT NOT NULL,
        FOREIGN KEY (категориальное_свойство_id) REFERENCES категориальные_свойства(идентификатор)
    );

    CREATE TABLE описание_свойств_породы (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        порода_id INTEGER NOT NULL,
        свойство_id INTEGER NOT NULL,
        активно BOOLEAN DEFAULT 1 NOT NULL CHECK (активно IN (0, 1)),
        FOREIGN KEY (порода_id) REFERENCES породa_собаки(идентификатор),
        FOREIGN KEY (свойство_id) REFERENCES свойство(идентификатор),
        UNIQUE(порода_id, свойство_id)
    );

    CREATE TABLE вещественное_значение_для_породы (
        описание_id INTEGER PRIMARY KEY,
        мин_значение REAL NOT NULL,
        макс_значение REAL NOT NULL,
        FOREIGN KEY (описание_id) REFERENCES описание_свойств_породы(идентификатор)
    );

    CREATE TABLE целое_значение_для_породы (
        описание_id INTEGER PRIMARY KEY,
        мин_значение INTEGER NOT NULL,
        макс_значение INTEGER NOT NULL,
        FOREIGN KEY (описание_id) REFERENCES описание_свойств_породы(идентификатор)
    );

    CREATE TABLE категориальное_значение_для_породы (
        идентификатор INTEGER PRIMARY KEY AUTOINCREMENT,
        описание_id INTEGER NOT NULL,
        категориальное_значение_id INTEGER NOT NULL,
        FOREIGN KEY (описание_id) REFERENCES описание_свойств_породы(идентификатор),
        FOREIGN KEY (категориальное_значение_id) REFERENCES категориальные_значения(идентификатор)
    ); 
    ''')

    conn.commit()
    print("✅ Схема базы данных создана (строго по разделу 3.7)")
    conn.close()

if __name__ == "__main__":
    init_database()