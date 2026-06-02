import joblib
import os
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler
from utils.db import get_db_connection

MODEL_PATH = "utils/dog_breed_model.pkl"
SCALER_PATH = "utils/scaler.pkl"
DATA_HASH_PATH = "utils/data_hash.txt"


def get_data_hash():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM породa_собаки")
    breeds = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM свойство")
    props = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM описание_свойств_породы")
    links = cur.fetchone()[0]
    conn.close()
    return f"{breeds}-{props}-{links}"


def is_model_valid():
    """Проверяет, можно ли использовать модель"""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(SCALER_PATH):
        return False
    if not os.path.exists(DATA_HASH_PATH):
        return False
    with open(DATA_HASH_PATH, 'r', encoding='utf-8') as f:
        saved = f.read().strip()
    return saved == get_data_hash()


def save_data_hash():
    with open(DATA_HASH_PATH, 'w', encoding='utf-8') as f:
        f.write(get_data_hash())


def train_model():
    """Обучает модель в wide формате (одна строка = одна порода)"""
    print(" Обучение модели RandomForest (wide format)...")
    
    conn = get_db_connection()
    
    # Wide формат: одна строка — одна порода
    query = """
    SELECT 
        п.название as breed,
        MAX(CASE WHEN с.название = 'вес' THEN (вм.мин_значение + вм.макс_значение)/2.0 END) as вес,
        MAX(CASE WHEN с.название = 'рост в холке' THEN (вм.мин_значение + вм.макс_значение)/2.0 END) as рост_в_холке,
        MAX(CASE WHEN с.название = 'продолжительность жизни' THEN (цм.мин_значение + цм.макс_значение)/2.0 END) as продолжительность_жизни,
        MAX(CASE WHEN с.название = 'тип шерсти' THEN кзн.значение END) as тип_шерсти,
        MAX(CASE WHEN с.название = 'темперамент' THEN кзн.значение END) as темперамент,
        MAX(CASE WHEN с.название = 'назначение' THEN кзн.значение END) as назначение
    FROM породa_собаки п
    JOIN описание_свойств_породы o ON o.порода_id = п.идентификатор AND o.активно = 1
    JOIN свойство с ON o.свойство_id = с.идентификатор
    LEFT JOIN вещественное_значение_для_породы вм ON вм.описание_id = o.идентификатор
    LEFT JOIN целое_значение_для_породы цм ON цм.описание_id = o.идентификатор
    LEFT JOIN категориальное_значение_для_породы кз ON кз.описание_id = o.идентификатор
    LEFT JOIN категориальные_значения кзн ON кзн.идентификатор = кз.категориальное_значение_id
    GROUP BY п.название
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        print(" Нет данных для обучения")
        return False

    # Нормализация числовых признаков
    numeric_cols = ['вес', 'рост_в_холке', 'продолжительность_жизни']
    scaler = MinMaxScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])

    # Категориальные признаки
    cat_cols = ['тип_шерсти', 'темперамент', 'назначение']
    X = pd.get_dummies(df[cat_cols + numeric_cols], columns=cat_cols, dummy_na=True)
    y = df['breed']

    model = RandomForestClassifier(
        n_estimators=500,
        max_features=None,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    save_data_hash()

    print(f"✅ Модель успешно обучена и сохранена! (пород: {len(y)})")
    return True


def predict_top3(user_input: dict):
    """Предсказывает топ-3 породы"""
    if not os.path.exists(MODEL_PATH) or not is_model_valid():
        return None, "Модель ИИ не может быть использована, потому что данные в базе были изменены."

    model = joblib.load(MODEL_PATH)
    scaler = joblib.load(SCALER_PATH)

    # Преобразуем ввод в wide формат
    row = {
        'вес': user_input.get('вес'),
        'рост_в_холке': user_input.get('рост в холке'),
        'продолжительность_жизни': user_input.get('продолжительность жизни'),
        'тип_шерсти': user_input.get('тип шерсти'),
        'темперамент': user_input.get('темперамент'),
        'назначение': user_input.get('назначение')
    }

    input_df = pd.DataFrame([row])
    numeric_cols = ['вес', 'рост_в_холке', 'продолжительность_жизни']
    input_df[numeric_cols] = scaler.transform(input_df[numeric_cols])

    X_input = pd.get_dummies(input_df, columns=['тип_шерсти', 'темперамент', 'назначение'], dummy_na=True)

    # Приводим к колонкам модели
    model_features = model.feature_names_in_
    for col in model_features:
        if col not in X_input.columns:
            X_input[col] = 0
    X_input = X_input[model_features]

    proba = model.predict_proba(X_input)[0]
    classes = model.classes_

    top_indices = proba.argsort()[-3:][::-1]
    top3 = [(classes[i], round(float(proba[i]) * 100, 1)) for i in top_indices]

    return top3, None

def invalidate_model():
    """Принудительно делает модель недействительной при любом изменении данных"""
    for path in [MODEL_PATH, SCALER_PATH, DATA_HASH_PATH]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
    print(" Модель ИИ инвалидирована (данные в базе изменены)")