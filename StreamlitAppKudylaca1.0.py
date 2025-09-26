import streamlit as st
import os
from typing import Dict, List, Tuple, Any
import tempfile

class MorphemicConlluSplitter:
    """Система морфемного анализа с разделением на три CONLLU файла"""
    
    def __init__(self):
        self.affix_features = {
            # Временные префиксы
            'ha': {'upos': 'PREF', 'feats': 'Tense=Past'},
            'ake': {'upos': 'PREF', 'feats': 'Tense=Present'},
            'ka': {'upos': 'PREF', 'feats': 'Tense=Future'},
            'to': {'upos': 'PREF', 'feats': 'Tense=Future'},
            'te': {'upos': 'PREF', 'feats': 'Tense=Present'},
            'ta': {'upos': 'PREF', 'feats': 'Tense=Past'},
            
            # Суффиксы
            'ye': {'upos': 'SUFF', 'feats': 'VerbForm=Fin'},
            'yemu': {'upos': 'SUFF', 'feats': 'VerbForm=Conv'},
            'yepi': {'upos': 'SUFF', 'feats': 'VerbForm=Part'},
            'mu': {'upos': 'SUFF', 'feats': 'Derivation=Quality'},
            'pi': {'upos': 'SUFF', 'feats': 'Derivation=Relation'}
        }
        
        # Словарь корней-существительных
        self.noun_roots = {
            'laca': 'человек', 'tala': 'смерть', 'laa': 'ветер', 
            'haka': 'огонь', 'naro': 'вода', 'ku': 'я', 'gy': 'ты',
            'ka': 'что', 'la': 'ветер', 'ranil': 'солнце', 'sari': 'пение'
        }
    
    def analyze_word(self, word: str) -> Dict:
        """Проводит морфемный анализ слова"""
        morphemes = self._split_into_morphemes(word)
        
        # Определяем UPOS корня
        root_upos = 'NOUN' if any(root in word for root in self.noun_roots) else 'VERB'
        
        return {
            'original_word': word,
            'morphemes': morphemes,
            'root_upos': root_upos
        }
    
    def _split_into_morphemes(self, word: str) -> List[Tuple[str, str]]:
        """Разбивает слово на морфемы с определением их типов"""
        morphemes = []
        remaining_word = word
        
        # Ищем префиксы
        prefixes_found = True
        while prefixes_found and remaining_word:
            prefixes_found = False
            for prefix in ['ake', 'ha', 'ka', 'to', 'te', 'ta']:
                if remaining_word.startswith(prefix):
                    morphemes.append((prefix, 'time_prefix'))
                    remaining_word = remaining_word[len(prefix):]
                    prefixes_found = True
                    break
        
        # Ищем корни (самый длинный совпадающий корень сначала)
        root_found = False
        for root in sorted(self.noun_roots.keys(), key=len, reverse=True):
            if remaining_word.startswith(root):
                morphemes.append((root, 'root'))
                remaining_word = remaining_word[len(root):]
                root_found = True
                break
        
        # Если корень не найден среди существительных, берем первую часть как корень
        if not root_found and remaining_word:
            # Эвристика: если слово короткое, это может быть местоимение
            if len(remaining_word) <= 2:
                morphemes.append((remaining_word, 'root'))
                remaining_word = ""
            else:
                # Пытаемся найти корень по паттернам
                for i in range(min(4, len(remaining_word)), 0, -1):
                    potential_root = remaining_word[:i]
                    if any(noun_root.startswith(potential_root) for noun_root in self.noun_roots):
                        morphemes.append((potential_root, 'root'))
                        remaining_word = remaining_word[i:]
                        break
                else:
                    # Берем первую часть как корень
                    root_length = min(3, len(remaining_word))
                    morphemes.append((remaining_word[:root_length], 'root'))
                    remaining_word = remaining_word[root_length:]
        
        # Ищем суффиксы
        suffixes_found = True
        while suffixes_found and remaining_word:
            suffixes_found = False
            for suffix in ['yepi', 'yemu', 'ye', 'mu', 'pi']:
                if remaining_word.endswith(suffix):
                    morphemes.append((suffix, 'suffix'))
                    remaining_word = remaining_word[:-len(suffix)]
                    suffixes_found = True
                    break
        
        # Остаток помечаем как unknown
        if remaining_word:
            morphemes.append((remaining_word, 'unknown'))
        
        return morphemes
    
    def generate_separate_conllu_files(self, words: List[str], base_output_path: str) -> Dict[str, str]:
        """Генерирует три отдельных CONLLU файла"""
        
        # Инициализируем содержимое файлов
        affixes_content = [
            "# affixes.conllu - только аффиксы", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        roots_content = [
            "# roots.conllu - только корни-существительные", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        other_content = [
            "# other.conllu - всё остальное", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        sentence_id = 1
        
        for word in words:
            analysis = self.analyze_word(word)
            morphemes = analysis['morphemes']
            
            # Генерируем записи для каждого типа морфем
            affix_records = []
            root_records = []
            other_records = []
            
            morpheme_position = 1
            
            for morpheme_form, morpheme_type in morphemes:
                conllu_line = self._create_conllu_line(
                    morpheme_form, morpheme_type, analysis, morpheme_position
                )
                
                # Распределяем по файлам
                if morpheme_type in ['time_prefix', 'suffix']:
                    affix_records.append(conllu_line)
                elif morpheme_type == 'root' and analysis['root_upos'] == 'NOUN':
                    root_records.append(conllu_line)
                else:
                    other_records.append(conllu_line)
                
                morpheme_position += 1
            
            # Добавляем в соответствующие файлы, если есть записи
            if affix_records:
                affixes_content.append(f"# sent_id = {sentence_id}")
                affixes_content.append(f"# text = {word}")
                affixes_content.extend(affix_records)
                affixes_content.append("")
            
            if root_records:
                roots_content.append(f"# sent_id = {sentence_id}")
                roots_content.append(f"# text = {word}")
                roots_content.extend(root_records)
                roots_content.append("")
            
            if other_records:
                other_content.append(f"# sent_id = {sentence_id}")
                other_content.append(f"# text = {word}")
                other_content.extend(other_records)
                other_content.append("")
            
            sentence_id += 1
        
        # Сохраняем файлы
        results = {}
        
        affixes_path = f"{base_output_path}_affixes.conllu"
        with open(affixes_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write("\n".join(affixes_content))
        results['affixes'] = affixes_path
        
        roots_path = f"{base_output_path}_roots.conllu"
        with open(roots_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write("\n".join(roots_content))
        results['roots'] = roots_path
        
        other_path = f"{base_output_path}_other.conllu"
        with open(other_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write("\n".join(other_content))
        results['other'] = other_path
        
        return results
    
    def generate_conllu_content(self, words: List[str]) -> Dict[str, str]:
        """Генерирует содержимое CONLLU файлов без сохранения на диск"""
        
        # Инициализируем содержимое файлов
        affixes_content = [
            "# affixes.conllu - только аффиксы", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        roots_content = [
            "# roots.conllu - только корни-существительные", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        other_content = [
            "# other.conllu - всё остальное", 
            "# language: kudylaca",
            "# sent_id | form | lemma | upos | xpos | feats | head | deprel | deps | misc",
            ""
        ]
        
        sentence_id = 1
        
        for word in words:
            analysis = self.analyze_word(word)
            morphemes = analysis['morphemes']
            
            # Генерируем записи для каждого типа морфем
            affix_records = []
            root_records = []
            other_records = []
            
            morpheme_position = 1
            
            for morpheme_form, morpheme_type in morphemes:
                conllu_line = self._create_conllu_line(
                    morpheme_form, morpheme_type, analysis, morpheme_position
                )
                
                # Распределяем по файлам
                if morpheme_type in ['time_prefix', 'suffix']:
                    affix_records.append(conllu_line)
                elif morpheme_type == 'root' and analysis['root_upos'] == 'NOUN':
                    root_records.append(conllu_line)
                else:
                    other_records.append(conllu_line)
                
                morpheme_position += 1
            
            # Добавляем в соответствующие файлы, если есть записи
            if affix_records:
                affixes_content.append(f"# sent_id = {sentence_id}")
                affixes_content.append(f"# text = {word}")
                affixes_content.extend(affix_records)
                affixes_content.append("")
            
            if root_records:
                roots_content.append(f"# sent_id = {sentence_id}")
                roots_content.append(f"# text = {word}")
                roots_content.extend(root_records)
                roots_content.append("")
            
            if other_records:
                other_content.append(f"# sent_id = {sentence_id}")
                other_content.append(f"# text = {word}")
                other_content.extend(other_records)
                other_content.append("")
            
            sentence_id += 1
        
        return {
            'affixes': "\n".join(affixes_content),
            'roots': "\n".join(roots_content),
            'other': "\n".join(other_content)
        }
    
    def _create_conllu_line(self, form: str, morpheme_type: str, analysis: Dict, position: int) -> str:
        """Создает строку CONLLU для морфемы"""
        
        # Базовые поля
        fields = {
            'id': str(position),
            'form': form,
            'lemma': form,
            'upos': 'X',
            'xpos': '_',
            'feats': '_',
            'head': '0',
            'deprel': 'root',
            'deps': '_',
            'misc': '_'
        }
        
        # Настраиваем в зависимости от типа морфемы
        if morpheme_type in ['time_prefix', 'suffix']:
            affix_info = self.affix_features.get(form, {})
            fields['upos'] = affix_info.get('upos', 'PREF' if morpheme_type == 'time_prefix' else 'SUFF')
            fields['feats'] = affix_info.get('feats', '_')
            fields['misc'] = f"Type={morpheme_type}"
            
        elif morpheme_type == 'root':
            if analysis['root_upos'] == 'NOUN':
                fields['upos'] = 'NOUN'
                meaning = self.noun_roots.get(form, 'unknown')
                fields['feats'] = f"Meaning={meaning}"
                fields['misc'] = "Type=root_noun"
            else:
                fields['upos'] = analysis['root_upos']
                fields['misc'] = f"Type=root_{analysis['root_upos'].lower()}"
                
        else:  # unknown
            fields['misc'] = f"NotMorpheme|Type={morpheme_type}"
        
        # Форматируем строку CONLLU
        return f"{fields['id']}\t{fields['form']}\t{fields['lemma']}\t{fields['upos']}\t{fields['xpos']}\t{fields['feats']}\t{fields['head']}\t{fields['deprel']}\t{fields['deps']}\t{fields['misc']}"

    def demonstrate_analysis(self, words: List[str]):
        """Демонстрация анализа слов"""
        st.subheader("📊 Результаты морфемного анализа")
        
        for word in words:
            st.write(f"**Слово:** `{word}`")
            analysis = self.analyze_word(word)
            morphemes = analysis['morphemes']
            
            # Отображаем морфемный разбор
            morphemes_text = " + ".join([f"{form} ({mtype})" for form, mtype in morphemes])
            st.write(f"**Морфемный разбор:** {morphemes_text}")
            
            # Показываем распределение по файлам
            affixes = [f for f, t in morphemes if t in ['time_prefix', 'suffix']]
            roots = [f for f, t in morphemes if t == 'root' and analysis['root_upos'] == 'NOUN']
            other = [f for f, t in morphemes if not (t in ['time_prefix', 'suffix'] or 
                                                     (t == 'root' and analysis['root_upos'] == 'NOUN'))]
            
            st.write("**Распределение по файлам CONLLU:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if affixes:
                    st.info(f"📁 **affixes.conllu:** {', '.join(affixes)}")
                else:
                    st.info("📁 **affixes.conllu:** -")
            
            with col2:
                if roots:
                    st.success(f"📁 **roots.conllu:** {', '.join(roots)}")
                else:
                    st.success("📁 **roots.conllu:** -")
            
            with col3:
                if other:
                    st.warning(f"📁 **other.conllu:** {', '.join(other)}")
                else:
                    st.warning("📁 **other.conllu:** -")
            
            st.divider()

def main():
    """Главная функция Streamlit приложения"""
    
    # Настройка страницы
    st.set_page_config(
        page_title="Morphemic Analyzer",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Заголовок приложения
    st.title("📚 Система морфемного анализа KUDYLACA")
    st.markdown("### с разделением на 3 CONLLU файла")
    
    # Инициализация анализатора
    if 'splitter' not in st.session_state:
        st.session_state.splitter = MorphemicConlluSplitter()
    
    splitter = st.session_state.splitter
    
    # Боковая панель с навигацией
    st.sidebar.title("Навигация")
    option = st.sidebar.radio(
        "Выберите опцию:",
        ["🏠 Главная", "🔍 Демонстрация анализа", "📝 Анализ своих слов", "💾 Создание CONLLU файлов"]
    )
    
    # Главная страница
    if option == "🏠 Главная":
        st.header("Добро пожаловать в систему морфемного анализа!")
        
        st.markdown("""
        Эта система выполняет морфемный анализ слов языка KUDYLACA и генерирует три отдельных CONLLU файла:
        
        - 📁 **affixes.conllu** - префиксы и суффиксы
        - 📁 **roots.conllu** - корни-существительные  
        - 📁 **other.conllu** - всё остальное
        
        ### Примеры слов для анализа:
        - `halacayemu` - человек (прошедшее время, деепричастие)
        - `takulaye` - я (будущее время, изъявительное наклонение)
        - `sarimu` - пение (качественное образование)
        - `aketolaye` - (настоящее/будущее время)
        """)
        
        # Быстрый тест
        if st.button("🚀 Быстрый тест на примерах"):
            test_words = ["halacayemu", "takulaye", "sarimu", "aketolaye", "gy", "tolacaye"]
            splitter.demonstrate_analysis(test_words)
    
    # Демонстрация анализа
    elif option == "🔍 Демонстрация анализа":
        st.header("Демонстрация морфемного анализа")
        
        st.info("""
        На этой странице вы можете увидеть анализ стандартных тестовых слов.
        Система покажет морфемный разбор каждого слова и его распределение по CONLLU файлам.
        """)
        
        test_words = ["halacayemu", "takulaye", "sarimu", "aketolaye", "gy", "tolacaye"]
        
        if st.button("Запустить демонстрацию"):
            splitter.demonstrate_analysis(test_words)
    
    # Анализ своих слов
    elif option == "📝 Анализ своих слов":
        st.header("Анализ пользовательских слов")
        
        st.info("""
        Введите слова для морфемного анализа. Каждое слово должно быть на отдельной строке.
        Примеры: `halacayemu`, `takulaye`, `sarimu`, `aketolaye`
        """)
        
        # Поле для ввода слов
        words_input = st.text_area(
            "Введите слова для анализа:",
            height=150,
            placeholder="halacayemu\ntakulaye\nsarimu\naketolaye"
        )
        
        if st.button("Анализировать слова"):
            if words_input.strip():
                words = [word.strip() for word in words_input.split('\n') if word.strip()]
                splitter.demonstrate_analysis(words)
            else:
                st.error("Пожалуйста, введите хотя бы одно слово для анализа.")
    
    # Создание CONLLU файлов
    elif option == "💾 Создание CONLLU файлов":
        st.header("Создание CONLLU файлов")
        
        st.info("""
        На этой странице вы можете ввести слова и получить три CONLLU файла с результатами анализа.
        Файлы можно будет просмотреть онлайн или скачать.
        """)
        
        # Поле для ввода слов
        words_input = st.text_area(
            "Введите слова для создания CONLLU файлов:",
            height=150,
            placeholder="halacayemu\ntakulaye\nsarimu\naketolaye",
            key="conllu_words"
        )
        
        base_filename = st.text_input("Базовое имя для файлов (без расширения):", value="morphemic_analysis")
        
        if st.button("Создать CONLLU файлы"):
            if words_input.strip():
                words = [word.strip() for word in words_input.split('\n') if word.strip()]
                
                # Генерируем содержимое файлов
                conllu_content = splitter.generate_conllu_content(words)
                
                # Показываем содержимое файлов
                st.success("✅ CONLLU файлы успешно созданы!")
                
                # Вкладки для просмотра содержимого
                tab1, tab2, tab3 = st.tabs(["📁 Affixes", "📁 Roots", "📁 Other"])
                
                with tab1:
                    st.subheader("affixes.conllu")
                    st.code(conllu_content['affixes'], language="text")
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="📥 Скачать affixes.conllu",
                        data=conllu_content['affixes'],
                        file_name=f"{base_filename}_affixes.conllu",
                        mime="text/plain"
                    )
                
                with tab2:
                    st.subheader("roots.conllu")
                    st.code(conllu_content['roots'], language="text")
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="📥 Скачать roots.conllu",
                        data=conllu_content['roots'],
                        file_name=f"{base_filename}_roots.conllu",
                        mime="text/plain"
                    )
                
                with tab3:
                    st.subheader("other.conllu")
                    st.code(conllu_content['other'], language="text")
                    
                    # Кнопка скачивания
                    st.download_button(
                        label="📥 Скачать other.conllu",
                        data=conllu_content['other'],
                        file_name=f"{base_filename}_other.conllu",
                        mime="text/plain"
                    )
                
                # Показываем анализ слов
                st.subheader("📊 Анализ слов")
                splitter.demonstrate_analysis(words)
                
            else:
                st.error("Пожалуйста, введите хотя бы одно слово для создания файлов.")
    
    # Информация о языке в боковой панели
    st.sidebar.markdown("---")
    st.sidebar.subheader("О языке KUDYLACA")
    st.sidebar.markdown("""
    **Корни-существительные:**
    - laca - человек
    - tala - смерть  
    - laa - ветер
    - haka - огонь
    - naro - вода
    
    **Аффиксы времени:**
    - ha/ta - прошедшее
    - ake/te - настоящее
    - ka/to - будущее
    """)

if __name__ == "__main__":
    main()