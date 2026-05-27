import streamlit as st
import pandas as pd
from utils.db import (
    get_all_breeds, get_all_properties, get_breed_values,
    get_breeds_for_editor, add_breed, delete_breed, 
    check_knowledge_completeness, reset_breeds_to_default,
    reset_breeds_to_default_safe,
    add_property,
    get_properties_for_editor,
    delete_property,
    reset_properties_to_default,
    get_properties_for_breed,
    update_breed_properties
)
from utils.solver import refute_hypotheses

st.set_page_config(page_title="Экспертная система. Классификация пород собак", layout="wide")
st.title("🐶 Экспертная система")
st.subheader("Классификация пород собак")

role = st.sidebar.radio("Роль:", ["Эксперт", "Специалист"], horizontal=True)

# ====================== ЭКСПЕРТ ======================
if role == "Эксперт":
    st.header("Редактор базы знаний")
    
    # Кнопка проверки полноты знаний
    if st.sidebar.button("🔍 Проверка полноты знаний", type="primary"):
        errors = check_knowledge_completeness()
        if "✅" in errors[0]:
            st.sidebar.success(errors[0])
        else:
            for err in errors:
                st.sidebar.error(err)
    
    expert_tabs = st.tabs(["Виды собак", "Свойства", "Возможные значения", 
                           "Описание свойств вида", "Значения для вида"])
    
    # 1. Виды собак — полноценное редактирование
    with expert_tabs[0]:
        st.subheader("Виды собак")
        
        # Добавление новой породы
        col1, col2 = st.columns([4, 1])
        with col1:
            new_breed = st.text_input("Название новой породы", 
                                    placeholder="Например: Шпиц",
                                    key="new_breed_input")
        with col2:
            if st.button("➕ Добавить породу", type="primary", use_container_width=True):
                if new_breed and new_breed.strip():
                    if add_breed(new_breed.strip()):
                        st.success(f"✅ Порода «{new_breed.strip()}» добавлена!")
                        st.rerun()
                    else:
                        st.error("Такая порода уже существует")
                else:
                    st.warning("Введите название породы")
        
        # Список всех пород
        breeds_df = get_breeds_for_editor()
        st.write("**Существующие породы**")
        
        # Выбор пород для удаления
        breeds_to_delete = st.multiselect(
            "Выберите породы для удаления",
            options=breeds_df['название'].tolist(),
            default=[],
            key="delete_multiselect"
        )
        
        col_del, col_reset = st.columns(2)
        
        with col_del:
            if st.button("🗑️ Удалить выбранные породы", type="secondary", use_container_width=True):
                if breeds_to_delete:
                    deleted = 0
                    for name in breeds_to_delete:
                        if delete_breed(name):
                            deleted += 1
                    if deleted > 0:
                        st.success(f"✅ Удалено {deleted} пород(ы)")
                        st.rerun()
                else:
                    st.warning("⚠️ Выберите хотя бы одну породу для удаления")
        
        with col_reset:
            if st.button("🔄 Восстановить исходные 20 пород", type="secondary", use_container_width=True):
                if reset_breeds_to_default_safe():
                    st.success("✅ Исходные породы восстановлены (добавлены недостающие)")
                    st.rerun()
        
        # Показ текущего списка
        st.dataframe(breeds_df, use_container_width=True, hide_index=True)
    
    with expert_tabs[1]:
        st.subheader("Свойства")
        
        # Добавление нового свойства
        col1, col2 = st.columns([4, 1])
        with col1:
            new_prop = st.text_input("Название нового свойства", 
                                   placeholder="Например: Цвет глаз или Длина хвоста",
                                   key="new_prop_input")
        with col2:
            if st.button("➕ Добавить свойство", type="primary", use_container_width=True):
                if new_prop and new_prop.strip():
                    if add_property(new_prop.strip()):
                        st.success(f"✅ Свойство «{new_prop.strip()}» добавлено!")
                        st.rerun()
                    else:
                        st.error("Такое свойство уже существует")
                else:
                    st.warning("Введите название свойства")
        
        # Список свойств
        props_df = get_properties_for_editor()
        st.write("**Существующие свойства**")
        
        # Выбор для удаления
        properties_to_delete = st.multiselect(
            "Выберите свойства для удаления",
            options=props_df['название'].tolist(),
            default=[],
            key="delete_props_multiselect"
        )
        
        col_del, col_reset = st.columns(2)
        
        with col_del:
            if st.button("🗑️ Удалить выбранные свойства", type="secondary", use_container_width=True):
                if properties_to_delete:
                    deleted = 0
                    for name in properties_to_delete:
                        if delete_property(name):
                            deleted += 1
                    if deleted > 0:
                        st.success(f"✅ Удалено {deleted} свойств(а)")
                        st.rerun()
                else:
                    st.warning("⚠️ Выберите хотя бы одно свойство для удаления")
        
        with col_reset:
            if st.button("🔄 Восстановить исходные 6 свойств", type="secondary", use_container_width=True):
                if reset_properties_to_default():
                    st.success("✅ Исходные свойства восстановлены!")
                    st.rerun()
        
        st.dataframe(props_df, use_container_width=True, hide_index=True)
    with expert_tabs[2]:
        st.subheader("Возможные значения")
        st.info("Редактирование диапазонов и списков значений (будет расширено)")
    with expert_tabs[3]:
        st.subheader("Описание свойств вида")
        
        breed = st.selectbox("Выберите породу", get_all_breeds()['название'], key="desc_breed")
        
        if breed:
            df = get_properties_for_breed(breed)
            all_properties = df['название'].tolist()
            
            st.write(f"**Выберите свойства для породы «{breed}»**")
            
            # Простые чекбоксы
            selected_props = []
            for prop in all_properties:
                if st.checkbox(prop, value=True, key=f"chk_{breed}_{prop}"):
                    selected_props.append(prop)
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Сохранить", type="primary", use_container_width=True):
                    if update_breed_properties(breed, selected_props):
                        st.success(f"✅ Свойства для «{breed}» сохранены")
            
            with col2:
                if st.button("🔄 Сбросить к полному набору (все 6 свойств)", 
                           type="secondary", use_container_width=True):
                    if update_breed_properties(breed, all_properties):
                        st.success(f"✅ Все свойства для породы «{breed}» возвращены (6 свойств)")
                        st.rerun()
            
            st.divider()
            st.caption("Выбранные свойства:")
            st.write(selected_props if selected_props else "Ничего не выбрано")
    with expert_tabs[4]:
        st.subheader("Значения для вида")
        b2 = st.selectbox("Порода", get_all_breeds()['название'], key="val_breed")
        if b2: st.dataframe(get_breed_values(b2), use_container_width=True, hide_index=True)

# ====================== СПЕЦИАЛИСТ ======================
else:
    spec_tabs = st.tabs(["Ввод исходных данных", "Просмотр базы знаний"])
    
    with spec_tabs[0]:
        st.header("Ввод исходных данных")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Числовые свойства")
            вес = st.number_input("Вес (кг)", value=35.0, step=0.1, format="%.1f")
            рост = st.number_input("Рост в холке (см)", value=60.0, step=0.1, format="%.1f")
            жизнь = st.number_input("Продолжительность жизни (лет)", value=12, step=1)
        
        with col2:
            st.subheader("Категориальные свойства")
            тип_шерсти = st.selectbox("Тип шерсти", ['Короткая', 'Средняя', 'Длинная'])
            темперамент = st.selectbox("Темперамент", ['Спокойный', 'Активный', 'Агрессивный', 'Дружелюбный'])
            назначение = st.selectbox("Назначение", ['Охотничья', 'Охранная', 'Декоративная', 'Служебная', 'Компаньон'])
        
        # === ЖЁСТКАЯ ВАЛИДАЦИЯ ===
        valid = (1.0 <= вес <= 90.0) and (15.0 <= рост <= 90.0) and (8 <= жизнь <= 18)
        
        if not valid:
            if not (1.0 <= вес <= 90.0):
                st.error("❌ Вес должен быть от 1 до 90 кг")
            if not (15.0 <= рост <= 90.0):
                st.error("❌ Рост в холке должен быть от 15 до 90 см")
            if not (8 <= жизнь <= 18):
                st.error("❌ Продолжительность жизни должна быть от 8 до 18 лет")
        
        # Кнопка — теперь надёжно отключена
        if st.button("🚀 Определить породу собаки", 
                     type="primary", 
                     use_container_width=True, 
                     disabled=not valid):
            user_input = {
                'вес': вес,
                'рост в холке': рост,
                'продолжительность жизни': жизнь,
                'тип шерсти': тип_шерсти,
                'темперамент': темперамент,
                'назначение': назначение
            }
            with st.spinner("Выполняется опровержение гипотез..."):
                possible, refuted, explanation = refute_hypotheses(user_input)
                st.session_state.user_input = user_input
                st.session_state.possible = possible
                st.session_state.refuted = refuted
                st.session_state.explanation = explanation
                st.session_state.show_result = True
            st.success("✅ Решение получено!")
        
        # Показ результата
        if st.session_state.get('show_result', False):
            st.divider()
            st.header("Результат и объяснение")
            possible = st.session_state.possible
            if len(possible) == 1:
                st.success(f"🎉 Порода: **{possible[0]}**")
            elif len(possible) > 1:
                st.warning(f"Подходят: {', '.join(possible)}")
            else:
                st.error("❌ Порода не определена")
            
            st.write(st.session_state.explanation)
            if st.session_state.refuted:
                st.subheader("Опровергнутые породы")
                for breed, reason in st.session_state.refuted:
                    st.markdown(f"**{breed}** — {reason}")

    with spec_tabs[1]:
        st.header("Просмотр базы знаний")
        selected = st.selectbox("Выберите породу", get_all_breeds()['название'].tolist())
        if selected:
            df = get_breed_values(selected)
            st.dataframe(df, use_container_width=True, hide_index=True)

st.sidebar.info("Экспертная система классификации пород собак")