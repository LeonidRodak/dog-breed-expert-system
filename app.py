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
    update_breed_properties,
    get_property_type,
    get_global_numeric_range,
    save_global_numeric_range,
    add_categorical_value,
    get_categorical_values,
    delete_categorical_value,
    get_breed_specific_value,
    save_breed_numeric_value,
    save_breed_categorical_values,
    get_db_connection,
    check_numeric_conflicts,
    trim_breed_numeric_values,
    check_categorical_conflicts,
    trim_breed_categorical_values,
    reset_possible_values_to_default,
    update_breed_properties_global,
    get_active_properties
)
from utils.solver import refute_hypotheses

st.set_page_config(page_title="Экспертная система. Классификация пород собак", layout="wide")
# Инициализация session_state
if 'show_reset_confirm' not in st.session_state:
    st.session_state.show_reset_confirm = False
st.title(" Экспертная система")
st.subheader("Классификация пород собак")

# ====================== ВЫБОР РОЛИ (disabled + сообщение) ======================
if 'current_role' not in st.session_state:
    st.session_state.current_role = "Эксперт"

# Проверяем полноту знаний один раз за рендер
check_result = check_knowledge_completeness()
is_complete = "Все данные заполнены корректно" in check_result[0]

# Показываем радио-кнопки
role = st.sidebar.radio(
    "Роль:", 
    ["Эксперт", "Специалист"], 
    horizontal=True,
    key="role_selector",
    disabled=not is_complete and st.session_state.current_role == "Эксперт",  # отключаем Специалист
    index=0 if st.session_state.current_role == "Эксперт" else 1
)

# Показываем предупреждение, если знаний недостаточно
if not is_complete:
    st.sidebar.error(" **Невозможно перейти в режим Специалиста!**")
    st.sidebar.info("Нажмите кнопку «Проверка полноты знаний», чтобы увидеть, что именно нужно заполнить.")

# Сохраняем выбранную роль
st.session_state.current_role = role

# ====================== ЭКСПЕРТ ======================
if role == "Эксперт":
    st.header("Редактор базы знаний")
    
    # Кнопка проверки полноты знаний
    if st.sidebar.button(" Проверка полноты знаний", type="primary"):
        errors = check_knowledge_completeness()
        if "Все данные заполнены корректно" in errors[0]:
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
        col1, col2 = st.columns([5, 2], vertical_alignment="bottom")
        with col1:
            new_breed = st.text_input("Название новой породы", 
                                    placeholder="Например: Шпиц",
                                    key="new_breed_input")
        with col2:
            if st.button(" Добавить породу", type="primary",use_container_width=True):
                if new_breed and new_breed.strip():
                    if add_breed(new_breed.strip()):
                        st.success(f" Порода «{new_breed.strip()}» успешно добавлена!\n"
                                f"К ней автоматически подключены все свойства.")
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
            if st.button(" Удалить выбранные породы", type="secondary", width="stretch"):
                if breeds_to_delete:
                    deleted = 0
                    for name in breeds_to_delete:
                        if delete_breed(name):
                            deleted += 1
                    if deleted > 0:
                        st.success(f" Удалено {deleted} пород(ы)")
                        st.rerun()
                else:
                    st.warning(" Выберите хотя бы одну породу для удаления")
        
        with col_reset:
            if st.button(" Восстановить исходные 20 пород", type="secondary", width="stretch"):
                if reset_breeds_to_default_safe():
                    st.success(" Исходные породы восстановлены (добавлены недостающие)")
                    st.rerun()
        
        # Показ текущего списка
        st.dataframe(breeds_df, width="stretch", hide_index=True)
    
    with expert_tabs[1]:
        st.subheader("Свойства")
        
        # Добавление нового свойства
        col1, col2, col3 = st.columns([4, 2, 2], vertical_alignment="bottom")
        with col1:
            new_prop = st.text_input("Название нового свойства", 
                                   placeholder="Например: Цвет глаз",
                                   key="new_prop_input")
        with col2:
            prop_type = st.selectbox(
                "Тип свойства",
                options=["вещественное", "целое", "категориальное"],
                key="new_prop_type"
            )
        with col3:
            if st.button(" Добавить свойство", type="primary", use_container_width=True):
                if new_prop and new_prop.strip():
                    if add_property(new_prop.strip(), prop_type):
                        st.success(f" Свойство «{new_prop.strip()}» ({prop_type}) добавлено ко всем породам!")
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
            if st.button("  Удалить выбранные свойства", type="secondary", width="stretch"):
                if properties_to_delete:
                    deleted = 0
                    for name in properties_to_delete:
                        if delete_property(name):
                            deleted += 1
                    if deleted > 0:
                        st.success(f" Удалено {deleted} свойств(а). Значения для пород сохранены!")
                        st.rerun()
                    else:
                        st.info("Ни одно свойство не было удалено")
                else:
                    st.warning("Выберите хотя бы одно свойство для удаления")
        
        with col_reset:
            if st.button(" Восстановить исходные 6 свойств", type="secondary", width="stretch"):
                if reset_properties_to_default():
                    st.success(" Исходные свойства восстановлены!")
                    st.rerun()
        
        st.dataframe(props_df, width="stretch", hide_index=True)
    with expert_tabs[2]:
        st.subheader("Возможные значения")
        st.caption("Редактирование глобальных диапазонов и списков допустимых значений свойств")
        
        # === КНОПКА ПОЛНОГО СБРОСА (независимая от других условий) ===
        if st.button(" Восстановить исходные возможные значения", 
                    type="secondary", 
                    width="stretch"):
            st.session_state.show_reset_confirm = True
            st.rerun()

        # === БЛОК ПОДТВЕРЖДЕНИЯ СБРОСА ===
        if st.session_state.get('show_reset_confirm', False):
            st.warning(" Вы действительно хотите сбросить ВСЕ глобальные диапазоны и значения пород к исходным из курсовой? Это действие **нельзя отменить**.")
            
            col_yes, col_no = st.columns(2)
            with col_yes:
                if st.button(" Да, сбросить всё", type="primary", width="stretch"):
                    print("=== КНОПКА 'Да, сбросить всё' НАЖАТА ===")
                    success = reset_possible_values_to_default()
                    print(f"Результат функции reset_possible_values_to_default: {success}")
                    if success:
                        st.success(" Все глобальные диапазоны и значения пород восстановлены к исходным!")
                        st.session_state.show_reset_confirm = False
                        st.rerun()
                    else:
                        st.error("Не удалось выполнить сброс (смотри терминал)")
            with col_no:
                if st.button(" Отмена", width="stretch"):
                    st.session_state.show_reset_confirm = False
                    st.rerun()
                    
        properties_df = get_all_properties()
        prop_names = properties_df['название'].tolist()
        
        selected_prop = st.selectbox(
            "Выберите свойство для редактирования:",
            options=prop_names,
            key="possible_values_prop_select"
        )
        
        if selected_prop:
            prop_type = get_property_type(selected_prop)
            
            st.divider()
            st.write(f"**Тип свойства:** {prop_type}")
            
            if prop_type in ["вещественное", "целое"]:
                st.subheader("Диапазон значений")
                current_range = get_global_numeric_range(selected_prop)
                
                min_key = f"min_input_{selected_prop}"
                max_key = f"max_input_{selected_prop}"
                
                col1, col2 = st.columns(2)
                with col1:
                    min_val = st.number_input(
                        "Минимальное значение",
                        value=current_range["min"] if current_range else (1.0 if prop_type == "вещественное" else 8),
                        step=0.1 if prop_type == "вещественное" else 1,
                        format="%.1f" if prop_type == "вещественное" else "%d",
                        key=min_key
                    )
                with col2:
                    max_val = st.number_input(
                        "Максимальное значение",
                        value=current_range["max"] if current_range else (90.0 if prop_type == "вещественное" else 18),
                        step=0.1 if prop_type == "вещественное" else 1,
                        format="%.1f" if prop_type == "вещественное" else "%d",
                        key=max_key
                    )
                
                # Кнопка сохранения диапазона
                if st.button(" Сохранить диапазон", type="primary", width="stretch"):
                    if min_val > max_val:
                        st.error("Минимальное значение не может быть больше максимального!")
                    else:
                        conflicts = check_numeric_conflicts(selected_prop, min_val, max_val)
                        
                        if conflicts:
                            # Сохраняем состояние конфликта в session_state
                            st.session_state.conflict_data = {
                                'prop': selected_prop,
                                'min': min_val,
                                'max': max_val,
                                'conflicts': conflicts
                            }
                            st.rerun()  # перезагрузка, чтобы показать кнопки выбора
                        else:
                            save_global_numeric_range(selected_prop, min_val, max_val)
                            st.success(f" Диапазон для «{selected_prop}» успешно сохранён!")
                            st.rerun()
            
            else:  # категориальное
                st.subheader("Допустимые значения")
                current_values = get_categorical_values(selected_prop)
                
                # === ДИНАМИЧЕСКАЯ ПОДСКАЗКА "Например: ..." ===
                if current_values:
                    examples = ", ".join(current_values[:4])  # показываем до 4 примеров
                    if len(current_values) > 4:
                        examples += ", ..."
                    st.caption(f"**Например:** {examples}")
                    placeholder_text = f"Например: {current_values[0]}"
                else:
                    st.caption("**Например:** — пока значений нет")
                    placeholder_text = "Например: Короткая"
                
                new_value = st.text_input(
                    "Новое значение", 
                    placeholder=placeholder_text,
                    key=f"new_cat_value_{selected_prop}"   # уникальный ключ, чтобы не было конфликтов
                )
                
                col_add, col_del = st.columns(2)
                with col_add:
                    if st.button(" Добавить значение", width="stretch"):
                        if new_value and new_value.strip():
                            add_categorical_value(selected_prop, new_value.strip())
                            st.success(f" Значение «{new_value.strip()}» добавлено!")
                            st.rerun()
                        else:
                            st.warning("Введите значение")
                
                with col_del:
                    if current_values:
                        value_to_delete = st.selectbox("Удалить значение", current_values, key=f"del_cat_value_{selected_prop}")
                        if st.button(" Удалить", width="stretch"):
                            remaining = [v for v in current_values if v != value_to_delete]
                            conflicts = check_categorical_conflicts(selected_prop, remaining)
                            if conflicts:
                                st.warning(" **Нарушение целостности знаний!**")
                                st.write("Следующие породы используют удаляемое значение:")
                                for breed, val in conflicts:
                                    st.write(f"• **{breed}** использует «{val}»")
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button(" Удалить и очистить у пород", type="primary", width="stretch"):
                                        delete_categorical_value(selected_prop, value_to_delete)
                                        trim_breed_categorical_values(selected_prop, remaining)
                                        st.success("Значение удалено и очищено у пород!")
                                        st.rerun()
                                with col2:
                                    if st.button(" Отменить", width="stretch"):
                                        st.rerun()
                            else:
                                delete_categorical_value(selected_prop, value_to_delete)
                                st.success(f"Значение «{value_to_delete}» удалено!")
                                st.rerun()
                
                st.write("**Все текущие значения:**", ", ".join(current_values) if current_values else "Пока пусто")
        
        # === БЛОК ОБРАБОТКИ КОНФЛИКТА (вне основного if) ===
        if st.session_state.get('conflict_data'):
            data = st.session_state.conflict_data
            st.warning(" **Нарушение целостности знаний!**")
            st.write(f"Свойство **{data['prop']}** — новый диапазон: {data['min']} — {data['max']}")
            st.write("Следующие породы имеют значения, выходящие за новый диапазон:")
            for breed, bmin, bmax in data['conflicts']:
                st.write(f"• **{breed}**: {bmin} — {bmax}")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button(" Обрезать автоматически", type="primary", width="stretch"):
                    success = trim_breed_numeric_values(data['prop'], data['min'], data['max'])
                    if success:
                        save_global_numeric_range(data['prop'], data['min'], data['max'])
                        st.success(" Диапазон сохранён + значения пород обрезаны!")
                    else:
                        st.error("Не удалось обрезать (смотри терминал)")
                    st.session_state.conflict_data = None
                    st.rerun()
            
            with col_b:
                if st.button(" Отменить", width="stretch"):
                    st.session_state.conflict_data = None
                    st.rerun()
    with expert_tabs[3]:
        st.subheader("Описание свойств вида")
        st.caption("Какие свойства используются для описания каждой породы")
        
        # ГЛОБАЛЬНАЯ КНОПКА ВВЕРХУ
        if st.button(" Восстановить исходные 6 свойств для всех пород", 
                    type="secondary", 
                    width="stretch"):
            if update_breed_properties_global():   # новая глобальная функция
                st.success(" Все свойства восстановлены у **всех** пород собак!")
                st.rerun()
        
        st.divider()
        
        # Выбор конкретной породы
        breed = st.selectbox(
            "Выберите породу для редактирования", 
            get_all_breeds()['название'].tolist(), 
            key="desc_breed"
        )
        
        if breed:
            df = get_properties_for_breed(breed)
            
            st.write(f"**Свойства для породы «{breed}»**")
            
            selected_props = []
            for _, row in df.iterrows():
                if st.checkbox(
                    row['название'], 
                    value=bool(row['selected']),
                    key=f"chk_desc_{breed}_{row['название']}"
                ):
                    selected_props.append(row['название'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button(" Сохранить для этой породы", type="primary", width="stretch"):
                    if update_breed_properties(breed, selected_props):
                        st.success(f" Описание свойств для «{breed}» обновлено!")
                        st.rerun()
            
            st.divider()
            st.caption("**Выбранные свойства:**")
            st.write(", ".join(selected_props) if selected_props else "Ничего не выбрано")
    with expert_tabs[4]:
        st.subheader("Значения для вида")
        st.caption("Конкретные диапазоны и списки значений для каждой породы")
        
        selected_breed = st.selectbox(
            "Выберите породу собаки:",
            options=get_all_breeds()['название'].tolist(),
            key="breed_values_select"
        )
        
        if selected_breed:
            st.divider()
            st.write(f"**Порода:** {selected_breed}")
            
            properties = get_all_properties()
            
            for idx, (_, prop) in enumerate(properties.iterrows()):
                prop_name = prop['название']
                prop_type = get_property_type(prop_name)
                
                with st.expander(f"**{prop_name}** ({prop_type})", expanded=False):
                    current = get_breed_specific_value(selected_breed, prop_name)
                    
                    if prop_type in ["вещественное", "целое"]:
                        global_range = get_global_numeric_range(prop_name)
                        
                        # Текущие значения породы (если есть)
                        current = get_breed_specific_value(selected_breed, prop_name)
                        default_min = current['min'] if current and current.get('type') in ['numeric', 'integer'] else (global_range['min'] if global_range else 0)
                        default_max = current['max'] if current and current.get('type') in ['numeric', 'integer'] else (global_range['max'] if global_range else 100)
                        
                        st.caption(f"**Глобальный диапазон:** {global_range['min']} — {global_range['max']}" if global_range else "Глобальный диапазон не задан")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            min_val = st.number_input("Мин", 
                                                    value=default_min,
                                                    step=0.1 if prop_type == "вещественное" else 1,
                                                    format="%.1f" if prop_type == "вещественное" else "%d",
                                                    key=f"min_{selected_breed}_{prop_name}")
                        with col2:
                            max_val = st.number_input("Макс", 
                                                    value=default_max,
                                                    step=0.1 if prop_type == "вещественное" else 1,
                                                    format="%.1f" if prop_type == "вещественное" else "%d",
                                                    key=f"max_{selected_breed}_{prop_name}")
                        
                        if st.button(" Сохранить диапазон", 
                                    key=f"save_num_{selected_breed}_{prop_name}",
                                    type="primary",
                                    width="stretch"):
                            if min_val > max_val:
                                st.error(" Минимальное значение не может быть больше максимального!")
                            elif global_range and (min_val < global_range['min'] or max_val > global_range['max']):
                                st.error(f" Диапазон породы **не может выходить** за глобальный диапазон!\n"
                                       f"Глобальный: **{global_range['min']} — {global_range['max']}**")
                            else:
                                save_breed_numeric_value(selected_breed, prop_name, min_val, max_val)
                                st.success(" Диапазон успешно сохранён!")
                                st.rerun()
                    
                    else:  # категориальное
                        global_values = get_categorical_values(prop_name)
                        current_vals = current['values'] if current and current.get('type') == 'categorical' else []
                        
                        selected_vals = st.multiselect(
                            "Допустимые значения",
                            options=global_values,
                            default=[v for v in current_vals if v in global_values],
                            key=f"cat_{selected_breed}_{prop_name}"
                        )
                        
                        if st.button(" Сохранить значения", 
                                    key=f"save_cat_{selected_breed}_{prop_name}",
                                    type="primary",
                                    width="stretch"):
                            save_breed_categorical_values(selected_breed, prop_name, selected_vals)
                            st.success("Сохранено!")
                            st.rerun()
            
            if st.button(" Посмотреть все значения породы", type="secondary", width="stretch"):
                st.dataframe(get_breed_values(selected_breed), width="stretch", hide_index=True)

# ====================== СПЕЦИАЛИСТ ======================
else:
    spec_tabs = st.tabs(["Ввод исходных данных", "Просмотр базы знаний"])
    
    with spec_tabs[0]:
        st.header("Ввод исходных данных")
        
        active_props = get_active_properties()
        
        if not active_props:
            st.warning("Нет активных свойств для ввода. Добавьте и включите свойства в режиме Эксперта.")
            st.stop()
        
        user_input = {}
        errors_input = []   # для сбора ошибок валидации
        
        st.subheader("Введите значения свойств собаки")
        
        for prop_name in active_props:
            prop_type = get_property_type(prop_name)
            
            with st.expander(f"**{prop_name}** ({prop_type})", expanded=True):
                if prop_type in ["вещественное", "целое"]:
                    global_range = get_global_numeric_range(prop_name)
                    
                    if global_range:
                        st.caption(f"**Глобальный диапазон:** {global_range['min']} — {global_range['max']}")
                    
                    value = st.number_input(
                        "Значение",
                        value=global_range['min'] if global_range else (1.0 if prop_type == "вещественное" else 8),
                        step=0.1 if prop_type == "вещественное" else 1,
                        format="%.1f" if prop_type == "вещественное" else "%d",
                        key=f"input_num_{prop_name}"
                    )
                    user_input[prop_name] = value
                    
                    # Проверка на выход за глобальный диапазон
                    if global_range and (value < global_range['min'] or value > global_range['max']):
                        errors_input.append(f"Свойство **{prop_name}** выходит за глобальный диапазон ({global_range['min']} — {global_range['max']})")
                
                else:  # категориальное
                    cat_values = get_categorical_values(prop_name)
                    if cat_values:
                        value = st.selectbox(
                            "Выберите значение",
                            options=cat_values,
                            key=f"input_cat_{prop_name}"
                        )
                        user_input[prop_name] = value
                    else:
                        st.warning("Нет допустимых значений для этого свойства")
        
        # Кнопка определения породы
        if st.button(" Определить породу собаки", type="primary", width="stretch"):
            if errors_input:
                for err in errors_input:
                    st.error(err)
            elif user_input:
                with st.spinner("Выполняется опровержение гипотез..."):
                    possible, refuted, explanation = refute_hypotheses(user_input)
                    st.session_state.user_input = user_input
                    st.session_state.possible = possible
                    st.session_state.refuted = refuted
                    st.session_state.explanation = explanation
                    st.session_state.show_result = True
                st.success(" Решение получено!")
            else:
                st.warning("Введите хотя бы одно свойство")
        
        # Показ результата
        if st.session_state.get('show_result', False):
            st.divider()
            st.header("Результат и объяснение")
            possible = st.session_state.possible
            if len(possible) == 1:
                st.success(f" Порода: **{possible[0]}**")
            elif len(possible) > 1:
                st.warning(f"Подходят несколько пород: {', '.join(possible)}")
            else:
                st.error(" Порода не определена")
            
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
            st.dataframe(df, width="stretch", hide_index=True)