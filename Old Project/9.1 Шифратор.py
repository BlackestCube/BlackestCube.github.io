class WordIDGenerator:
    def __init__(self):
        # Базовые алфавиты
        self.consonants = sorted(['b', 'c', 'd', 'f', 'g', 'h', 'j', 'k', 'l', 'm', 
                                'n', 'p', 'q', 'r', 's', 't', 'v', 'w', 'x', 'z'])
        
        self.vowels = sorted(['a', 'e', 'i', 'o', 'u', 'y'])
        
        # 32-ричный алфавит
        self.base32_alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
        
        # Грамматические суффиксы для частей речи
        self.grammar_suffixes = {
            'participle': {'suffix': 'yepi', 'label': 'Причастие'},
            'gerund': {'suffix': 'yemu', 'label': 'Деепричастие'},
            'adjective': {'suffix': 'pi', 'label': 'Прилагательное'},
            'verb': {'suffix': 'ye', 'label': 'Глагол'},
            'adverb': {'suffix': 'mu', 'label': 'Наречие'}
        }
        
        # Грамматические приставки с приоритетами
        self.grammar_prefixes = {
            # Временные приставки (первый уровень)
            'ha': {'prefix': 'ha', 'label': 'Прошедшее время', 'priority': 1},
            'ake': {'prefix': 'ake', 'label': 'Настоящее время', 'priority': 1},
            'ka': {'prefix': 'ka', 'label': 'Будущее время', 'priority': 1},
            
            # Модальные приставки (второй уровень - в порядке значимости)
            'to': {'prefix': 'to', 'label': 'Абсолютизм', 'priority': 2},
            'te': {'prefix': 'te', 'label': 'Неопределённость', 'priority': 3},
            'ta': {'prefix': 'ta', 'label': 'Отсутствие', 'priority': 4}
        }
        
        # Для статистики
        self.stats = {"words_processed": 0, "syllables_processed": 0, "grammar_processed": 0}
    
    def _to_base32(self, number):
        """Конвертирует число в 32-ричную систему"""
        if number == 0:
            return self.base32_alphabet[0]
        
        result = ''
        n = number
        while n > 0:
            n, remainder = divmod(n, 32)
            result = self.base32_alphabet[remainder] + result
        return result.zfill(2)
    
    def _from_base32(self, base32_str):
        """Конвертирует из 32-ричной системы в десятичную"""
        result = 0
        for char in base32_str:
            result = result * 32 + self.base32_alphabet.index(char)
        return result
    
    def _char_to_code(self, char):
        """Конвертирует символ в числовой код"""
        if char in self.consonants:
            return self.consonants.index(char) + 1
        elif char in self.vowels:
            return 21 + self.vowels.index(char)
        else:
            return 0
    
    def _code_to_char(self, code):
        """Конвертирует числовой код обратно в символ"""
        if 1 <= code <= 20:
            return self.consonants[code - 1]
        elif 21 <= code <= 26:
            vowel_code = code - 21
            return self.vowels[vowel_code] if vowel_code < len(self.vowels) else '?'
        else:
            return '?'
    
    def encode_syllable(self, syllable):
        """Кодирование слога длиной до 3 символов"""
        if not syllable:
            return "00"
        
        code = 0
        for i, char in enumerate(syllable):
            char_code = self._char_to_code(char)
            code = code * 32 + char_code
        
        return self._to_base32(code)
    
    def decode_syllable(self, code):
        """Декодирование слога из кода"""
        num = self._from_base32(code)
        
        chars = []
        while num > 0:
            remainder = num % 32
            if remainder > 0:
                chars.append(self._code_to_char(remainder))
            num = num // 32
        
        return ''.join(reversed(chars))
    
    def _is_valid_stem(self, stem):
        """Проверяет, является ли основа допустимой (минимум 2 буквы и 1 слог)"""
        if len(stem) < 2:
            return False
        
        # Проверяем наличие хотя бы одной гласной (слог)
        has_vowel = any(char in self.vowels for char in stem)
        return has_vowel
    
    def _detect_grammar_affixes(self, word):
        """Улучшенный алгоритм распознавания грамматических аффиксов"""
        original_word = word
        detected_affixes = {
            'time_prefix': None,
            'modality_prefixes': [],  # Список модальных приставок
            'suffix': None,
            'stem': word
        }
        
        # 1. Сначала ищем временную приставку (только одну)
        time_prefixes = [p for p in self.grammar_prefixes.values() if p['priority'] == 1]
        time_prefixes.sort(key=lambda x: len(x['prefix']), reverse=True)
        
        for prefix_info in time_prefixes:
            prefix = prefix_info['prefix']
            if word.startswith(prefix):
                # Проверяем, что после приставки остается допустимая основа
                remaining = word[len(prefix):]
                if self._is_valid_stem(remaining):
                    detected_affixes['time_prefix'] = prefix_info
                    word = remaining
                    break
        
        # 2. Затем ищем модальные приставки (может быть несколько)
        modality_prefixes = [p for p in self.grammar_prefixes.values() if p['priority'] > 1]
        modality_prefixes.sort(key=lambda x: x['priority'])  # Сортируем по приоритету
        
        # Ищем модальные приставки в правильном порядке
        found_modality = True
        while found_modality and word:
            found_modality = False
            for prefix_info in modality_prefixes:
                prefix = prefix_info['prefix']
                if word.startswith(prefix):
                    # Проверяем, что после всех приставок остается допустимая основа
                    remaining_after_all = word[len(prefix):]
                    
                    # Проверяем суффикс
                    suffix_found = False
                    for suffix_info in self.grammar_suffixes.values():
                        if remaining_after_all.endswith(suffix_info['suffix']):
                            stem = remaining_after_all[:-len(suffix_info['suffix'])]
                            if self._is_valid_stem(stem):
                                suffix_found = True
                                break
                    
                    # Если не нашли суффикс, проверяем основу
                    if not suffix_found and self._is_valid_stem(remaining_after_all):
                        suffix_found = True
                    
                    if suffix_found:
                        detected_affixes['modality_prefixes'].append(prefix_info)
                        word = word[len(prefix):]
                        found_modality = True
                        break
        
        # 3. Ищем суффикс части речи
        suffix_candidates = sorted(
            self.grammar_suffixes.values(),
            key=lambda x: len(x['suffix']),
            reverse=True
        )
        
        for suffix_info in suffix_candidates:
            suffix = suffix_info['suffix']
            if word.endswith(suffix):
                stem = word[:-len(suffix)]
                if self._is_valid_stem(stem):
                    detected_affixes['suffix'] = suffix_info
                    word = stem
                    break
        
        # 4. Проверяем основу
        if not self._is_valid_stem(word):
            # Если основа недопустима, откатываем изменения
            return self._fallback_detection(original_word)
        
        detected_affixes['stem'] = word
        return detected_affixes
    
    def _fallback_detection(self, word):
        """Резервный алгоритм распознавания для коротких слов"""
        # Простой алгоритм для слов с короткой основой
        detected_affixes = {
            'time_prefix': None,
            'modality_prefixes': [],
            'suffix': None,
            'stem': word
        }
        
        # Пробуем найти только суффикс
        for suffix_info in self.grammar_suffixes.values():
            if word.endswith(suffix_info['suffix']):
                stem = word[:-len(suffix_info['suffix'])]
                if len(stem) >= 2:  # Минимум 2 буквы в основе
                    detected_affixes['suffix'] = suffix_info
                    detected_affixes['stem'] = stem
                    break
        
        return detected_affixes
    
    def _get_syllable_count(self, word):
        """Оценивает количество слогов в слове"""
        vowel_count = sum(1 for char in word if char in self.vowels)
        return max(1, vowel_count)
    
    def word_to_syllables(self, word, delimiter='-'):
        """Разбивает слово на слоги с учетом грамматических аффиксов"""
        if delimiter and delimiter in word:
            return word.split(delimiter)
        else:
            return self._improved_syllable_split(word)
    
    def _improved_syllable_split(self, word):
        """Улучшенный алгоритм разбиения на слоги"""
        if not word:
            return []
        
        # Анализируем грамматические аффиксы
        affix_info = self._detect_grammar_affixes(word)
        
        syllables = []
        
        # Добавляем временную приставку
        if affix_info['time_prefix']:
            syllables.append(affix_info['time_prefix']['prefix'])
        
        # Добавляем модальные приставки
        for modality in affix_info['modality_prefixes']:
            syllables.append(modality['prefix'])
        
        # Разбиваем основу на слоги (может быть 1 слог из 2 букв)
        stem_syllables = self._split_stem_into_syllables(affix_info['stem'])
        syllables.extend(stem_syllables)
        
        # Добавляем суффикс
        if affix_info['suffix']:
            suffix_syllables = self._split_suffix_into_syllables(affix_info['suffix']['suffix'])
            syllables.extend(suffix_syllables)
        
        return syllables
    
    def _split_stem_into_syllables(self, stem):
        """Разбивает основу слова на слоги (основа может быть из 2 букв - 1 слог)"""
        if not stem:
            return []
        
        # Если основа короткая (2-3 буквы), считаем ее одним слогом
        if len(stem) <= 3:
            return [stem]
        
        syllables = []
        current_syllable = ""
        
        for i, char in enumerate(stem):
            current_syllable += char
            
            # Простые правила разбиения для более длинных основ
            if len(current_syllable) >= 3:
                syllables.append(current_syllable)
                current_syllable = ""
            elif i == len(stem) - 1:
                syllables.append(current_syllable)
            elif char in self.vowels and i < len(stem) - 1:
                next_char = stem[i + 1]
                if next_char in self.vowels:
                    syllables.append(current_syllable)
                    current_syllable = ""
        
        return syllables
    
    def _split_suffix_into_syllables(self, suffix):
        """Разбивает суффикс на слоги"""
        syllables = []
        current = ""
        
        for char in suffix:
            current += char
            if char in self.vowels:
                syllables.append(current)
                current = ""
        
        if current:
            if syllables:
                syllables[-1] += current
            else:
                syllables.append(current)
        
        return syllables
    
    def word_to_id(self, word, delimiter='-', include_length=True, include_grammar=True):
        """Преобразует слово в уникальный ID"""
        # Анализируем грамматические аффиксы
        affix_info = self._detect_grammar_affixes(word)
        
        # Разбиваем на слоги
        syllables = self.word_to_syllables(word, delimiter)
        
        # Кодируем каждый слог
        codes = []
        for syllable in syllables:
            code = self.encode_syllable(syllable)
            codes.append(code)
        
        # Объединяем коды
        id_string = ''.join(codes)
        
        # Добавляем информацию о количестве слогов
        if include_length:
            length_code = self._to_base32(len(syllables))
            id_string = length_code + id_string
        
        # Добавляем грамматическую информацию
        if include_grammar:
            grammar_code = self._grammar_affixes_to_code(affix_info)
            id_string += grammar_code
            self.stats["grammar_processed"] += 1
        
        # Статистика
        self.stats["words_processed"] += 1
        self.stats["syllables_processed"] += len(syllables)
        
        return id_string
    
    def _grammar_affixes_to_code(self, affix_info):
        """Кодирует грамматические аффиксы в специальный код"""
        # Временная приставка - 2 символа
        time_code = '00'
        if affix_info['time_prefix']:
            time_map = {'ha': 'TP', 'ake': 'TN', 'ka': 'TF'}
            time_code = time_map.get(affix_info['time_prefix']['prefix'], '00')
        
        # Модальные приставки - 2 символа (битовая маска)
        modality_code = '00'
        if affix_info['modality_prefixes']:
            mask = 0
            for modality in affix_info['modality_prefixes']:
                if modality['prefix'] == 'to':
                    mask |= 1  # 001
                elif modality['prefix'] == 'te':
                    mask |= 2  # 010
                elif modality['prefix'] == 'ta':
                    mask |= 4  # 100
            
            # Кодируем маску в 2 символа base32
            modality_code = self._to_base32(mask)
        
        # Суффикс - 2 символа
        suffix_code = '00'
        if affix_info['suffix']:
            suffix_map = {
                'adjective': 'SA', 'participle': 'SP', 'verb': 'SV',
                'adverb': 'SD', 'gerund': 'SG'
            }
            suffix_code = suffix_map.get(affix_info['suffix']['prefix'], '00')
        
        return time_code + modality_code + suffix_code
    
    def _code_to_grammar_affixes(self, code):
        """Декодирует грамматические аффиксы из кода"""
        if len(code) != 6:
            return {}
        
        time_code = code[:2]
        modality_code = code[2:4]
        suffix_code = code[4:6]
        
        # Временные приставки
        time_map = {
            'TP': ('ha', 'Прошедшее время'),
            'TN': ('ake', 'Настоящее время'),
            'TF': ('ka', 'Будущее время')
        }
        
        # Суффиксы
        suffix_map = {
            'SA': ('adjective', 'Прилагательное'),
            'SP': ('participle', 'Причастие'),
            'SV': ('verb', 'Глагол'),
            'SD': ('adverb', 'Наречие'),
            'SG': ('gerund', 'Деепричастие')
        }
        
        time_info = time_map.get(time_code, (None, None))
        suffix_info = suffix_map.get(suffix_code, (None, None))
        
        # Декодируем модальные приставки из битовой маски
        modality_mask = self._from_base32(modality_code)
        modalities = []
        
        if modality_mask & 1:  # to
            modalities.append(('to', 'Абсолютизм'))
        if modality_mask & 2:  # te
            modalities.append(('te', 'Неопределённость'))
        if modality_mask & 4:  # ta
            modalities.append(('ta', 'Отсутствие'))
        
        return {
            'time_prefix': time_info[0],
            'time_label': time_info[1],
            'modality_prefixes': modalities,
            'suffix_part': suffix_info[0],
            'suffix_label': suffix_info[1]
        }
    
    def id_to_word(self, id_string, delimiter='-', include_length=True, include_grammar=True):
        """Восстанавливает слово из ID"""
        grammar_info = {}
        
        if include_grammar and len(id_string) >= 6:
            grammar_code = id_string[-6:]
            grammar_info = self._code_to_grammar_affixes(grammar_code)
            id_string = id_string[:-6]
        
        if include_length:
            length_code = id_string[:2]
            syllable_count = self._from_base32(length_code)
            code_part = id_string[2:]
        else:
            code_part = id_string
            syllable_count = len(code_part) // 2
        
        # Декодируем слоги
        syllables = []
        for i in range(syllable_count):
            start = i * 2
            end = start + 2
            if end <= len(code_part):
                code = code_part[start:end]
                syllable = self.decode_syllable(code)
                syllables.append(syllable)
        
        word = delimiter.join(syllables)
        
        # Восстанавливаем грамматические аффиксы
        reconstructed_word = word
        
        # Добавляем модальные приставки (в обратном порядке)
        if 'modality_prefixes' in grammar_info:
            for modality in reversed(grammar_info['modality_prefixes']):
                if modality[0] and not reconstructed_word.startswith(modality[0]):
                    reconstructed_word = modality[0] + reconstructed_word
        
        # Добавляем временную приставку
        if grammar_info.get('time_prefix') and not reconstructed_word.startswith(grammar_info['time_prefix']):
            reconstructed_word = grammar_info['time_prefix'] + reconstructed_word
        
        # Добавляем суффикс
        if grammar_info.get('suffix_part'):
            suffix = self.grammar_suffixes[grammar_info['suffix_part']]['suffix']
            if not reconstructed_word.endswith(suffix):
                reconstructed_word = reconstructed_word + suffix
        
        return reconstructed_word, grammar_info
    
    def detect_word_grammar(self, word):
        """Определяет грамматическую информацию о слове"""
        affix_info = self._detect_grammar_affixes(word)
        
        grammar_notes = []
        
        # Формируем описание
        if affix_info['time_prefix']:
            grammar_notes.append(f"Время: {affix_info['time_prefix']['label']}")
        
        if affix_info['modality_prefixes']:
            modalities = [modality['label'] for modality in affix_info['modality_prefixes']]
            grammar_notes.append(f"Модальности: {', '.join(modalities)}")
            
            # Специальные случаи
            if len(affix_info['modality_prefixes']) >= 2:
                grammar_notes.append("Сложная модальная конструкция")
        
        if affix_info['suffix']:
            grammar_notes.append(f"Часть речи: {affix_info['suffix']['label']}")
        
        # Проверяем основу
        if self._is_valid_stem(affix_info['stem']):
            syllable_count = self._get_syllable_count(affix_info['stem'])
            grammar_notes.append(f"Основа: {affix_info['stem']} ({syllable_count} слог{'а' if syllable_count > 1 else ''})")
        else:
            grammar_notes.append(f"Основа: {affix_info['stem']} (короткая основа)")
        
        return {
            'word': word,
            'time_prefix': affix_info['time_prefix'],
            'modality_prefixes': affix_info['modality_prefixes'],
            'suffix': affix_info['suffix'],
            'stem': affix_info['stem'],
            'syllables': self.word_to_syllables(word, '-'),
            'grammar_notes': grammar_notes
        }
    
    def get_grammar_info(self):
        """Возвращает информацию о грамматических аффиксах"""
        info = []
        
        # Временные приставки
        for prefix in [p for p in self.grammar_prefixes.values() if p['priority'] == 1]:
            info.append({
                'type': 'time',
                'label': prefix['label'],
                'affix': prefix['prefix'],
                'example': f"{prefix['prefix']}слово"
            })
        
        # Модальные приставки
        for prefix in [p for p in self.grammar_prefixes.values() if p['priority'] > 1]:
            info.append({
                'type': 'modality',
                'label': prefix['label'],
                'affix': prefix['prefix'],
                'example': f"{prefix['prefix']}слово"
            })
        
        # Суффиксы
        for suffix in self.grammar_suffixes.values():
            info.append({
                'type': 'suffix',
                'label': suffix['label'],
                'affix': suffix['suffix'],
                'example': f"слово{suffix['suffix']}"
            })
        
        return info
    
    def get_collision_probability(self, word_count=1000000):
        """Оценивает вероятность коллизий"""
        total_combinations = 1024
        
        if word_count > total_combinations:
            return 1.0
        
        collision_prob = 1 - pow(1 - 1/total_combinations, word_count*(word_count-1)/2)
        return collision_prob
    
    def print_stats(self):
        """Выводит статистику использования"""
        print("Статистика генератора ID:")
        print(f"Обработано слов: {self.stats['words_processed']}")
        print(f"Обработано слогов: {self.stats['syllables_processed']}")
        print(f"Обработано слов с грамматикой: {self.stats['grammar_processed']}")
        if self.stats['words_processed'] > 0:
            avg_syllables = self.stats['syllables_processed'] / self.stats['words_processed']
            print(f"Среднее количество слогов на слово: {avg_syllables:.2f}")


def display_menu():
    """Отображает главное меню"""
    print("\n" + "=" * 60)
    print("           ГЕНЕРАТОР УНИКАЛЬНЫХ ID ДЛЯ СЛОВ")
    print("=" * 60)
    print("1. Кодировать слово в ID")
    print("2. Декодировать ID в слово")
    print("3. Анализ грамматики слова")
    print("4. Показать грамматические аффиксы")
    print("5. Показать статистику")
    print("6. Оценить вероятность коллизий")
    print("7. Тестовые примеры")
    print("8. О программе")
    print("0. Выход")
    print("-" * 60)


def encode_word(generator):
    """Кодирование слова в ID"""
    print("\n--- КОДИРОВАНИЕ СЛОВА В ID ---")
    word = input("Введите слово для кодирования: ").strip()
    
    if not word:
        print("Ошибка: слово не может быть пустым.")
        return
    
    delimiter = input("Введите разделитель слогов (или нажмите Enter для автоопределения): ").strip()
    if not delimiter:
        delimiter = '-'
    
    include_length = input("Включить информацию о длине в ID? (y/n, по умолчанию y): ").strip().lower()
    include_length = include_length != 'n'
    
    include_grammar = input("Включить грамматическую информацию? (y/n, по умолчанию y): ").strip().lower()
    include_grammar = include_grammar != 'n'
    
    try:
        # Анализируем грамматику слова
        grammar_info = generator.detect_word_grammar(word)
        
        print(f"\nАнализ слова:")
        print(f"Слово: {word}")
        
        if grammar_info['time_prefix']:
            print(f"Временная приставка: {grammar_info['time_prefix']['prefix']} ({grammar_info['time_prefix']['label']})")
        
        if grammar_info['modality_prefixes']:
            print("Модальные приставки:")
            for modality in grammar_info['modality_prefixes']:
                print(f"  - {modality['prefix']} ({modality['label']})")
        
        if grammar_info['suffix']:
            print(f"Суффикс: {grammar_info['suffix']['suffix']} ({grammar_info['suffix']['label']})")
        
        print(f"Основа: {grammar_info['stem']}")
        print(f"Слоги: {'-'.join(grammar_info['syllables'])}")
        
        if grammar_info['grammar_notes']:
            print(f"Грамматические особенности:")
            for note in grammar_info['grammar_notes']:
                print(f"  • {note}")
        
        # Генерируем ID
        word_id = generator.word_to_id(word, delimiter, include_length, include_grammar)
        compact_id = generator.word_to_id(word, delimiter, False, include_grammar)
        
        print(f"\nРезультат кодирования:")
        print(f"Полный ID: {word_id}")
        print(f"Компактный ID: {compact_id}")
        print(f"Разделитель: '{delimiter}'")
        
        # Проверка обратного преобразования
        if include_grammar:
            reconstructed, grammar_label = generator.id_to_word(word_id, delimiter, include_length, include_grammar)
        else:
            reconstructed, _ = generator.id_to_word(word_id, delimiter, include_length, False)
        
        print(f"Проверка (декодирование): {reconstructed}")
        
        if word.lower() == reconstructed.lower():
            print("✅ Слово успешно восстановлено!")
            if include_grammar and grammar_label:
                for key, value in grammar_label.items():
                    if value:
                        if key == 'modality_prefixes':
                            modalities = [f"{mod[0]} ({mod[1]})" for mod in value]
                            print(f"✅ Модальные приставки: {', '.join(modalities)}")
                        elif key == 'time_label':
                            print(f"✅ Временная приставка: {value}")
                        elif key == 'suffix_label':
                            print(f"✅ Суффикс: {value}")
        else:
            print("⚠️  Внимание: восстановленное слово не полностью совпадает с оригиналом")
            print(f"   Оригинал: {word}")
            print(f"   Восстановлено: {reconstructed}")
        
    except Exception as e:
        print(f"Ошибка при кодировании: {e}")


def decode_id(generator):
    """Декодирование ID в слово"""
    print("\n--- ДЕКОДИРОВАНИЕ ID В СЛОВО ---")
    id_string = input("Введите ID для декодирования: ").strip()
    
    if not id_string:
        print("Ошибка: ID не может быть пустым.")
        return
    
    delimiter = input("Введите разделитель слогов (или нажмите Enter для '-'): ").strip()
    if not delimiter:
        delimiter = '-'
    
    include_length = input("ID включает информацию о длине? (y/n, по умолчанию y): ").strip().lower()
    include_length = include_length != 'n'
    
    include_grammar = input("ID включает грамматическую информацию? (y/n, по умолчанию y): ").strip().lower()
    include_grammar = include_grammar != 'n'
    
    try:
        word, grammar_info = generator.id_to_word(id_string, delimiter, include_length, include_grammar)
        
        print(f"\nРезультат декодирования:")
        print(f"ID: {id_string}")
        print(f"Слово: {word}")
        
        if grammar_info:
            if grammar_info.get('time_label'):
                print(f"Определенная временная приставка: {grammar_info['time_label']}")
            
            if grammar_info.get('modality_prefixes'):
                modalities = [f"{mod[0]} ({mod[1]})" for mod in grammar_info['modality_prefixes']]
                print(f"Определенные модальные приставки: {', '.join(modalities)}")
            
            if grammar_info.get('suffix_label'):
                print(f"Определенный суффикс: {grammar_info['suffix_label']}")
        
        print(f"Разделитель: '{delimiter}'")
        
    except Exception as e:
        print(f"Ошибка при декодировании: {e}")


def analyze_grammar(generator):
    """Анализ грамматики слова"""
    print("\n--- АНАЛИЗ ГРАММАТИКИ СЛОВА ---")
    word = input("Введите слово для анализа: ").strip()
    
    if not word:
        print("Ошибка: слово не может быть пустым.")
        return
    
    try:
        grammar_info = generator.detect_word_grammar(word)
        
        print(f"\nРезультат анализа:")
        print(f"Слово: {grammar_info['word']}")
        
        if grammar_info['time_prefix']:
            print(f"Временная приставка: {grammar_info['time_prefix']['prefix']} ({grammar_info['time_prefix']['label']})")
        else:
            print("Временная приставка: не определена")
        
        if grammar_info['modality_prefixes']:
            print("Модальные приставки:")
            for modality in grammar_info['modality_prefixes']:
                print(f"  - {modality['prefix']} ({modality['label']})")
        else:
            print("Модальные приставки: не определены")
        
        if grammar_info['suffix']:
            print(f"Суффикс: {grammar_info['suffix']['suffix']} ({grammar_info['suffix']['label']})")
        else:
            print("Суффикс: не определена")
        
        print(f"Основа: {grammar_info['stem']}")
        print(f"Слоги: {'-'.join(grammar_info['syllables'])}")
        
        if grammar_info['grammar_notes']:
            print(f"Грамматические особенности:")
            for note in grammar_info['grammar_notes']:
                print(f"  • {note}")
        
        # Показываем доступные аффиксы
        print(f"\nДоступные грамматические аффиксы:")
        grammar_info_list = generator.get_grammar_info()
        for info in grammar_info_list:
            status = "✓" if ((info['type'] == 'time' and grammar_info['time_prefix'] and 
                             info['affix'] == grammar_info['time_prefix']['prefix']) or
                            (info['type'] == 'modality' and any(m['prefix'] == info['affix'] 
                             for m in grammar_info['modality_prefixes'])) or
                            (info['type'] == 'suffix' and grammar_info['suffix'] and 
                             info['affix'] == grammar_info['suffix']['suffix'])) else " "
            print(f"  {status} {info['type']:9} {info['label']:20} ({info['affix']:5}) пример: {info['example']}")
        
    except Exception as e:
        print(f"Ошибка при анализе: {e}")


def show_grammar_affixes(generator):
    """Показывает все грамматические аффиксы"""
    print("\n--- ГРАММАТИЧЕСКИЕ АФФИКСЫ ---")
    
    grammar_info_list = generator.get_grammar_info()
    
    print("Тип       | Назначение           | Аффикс | Пример")
    print("-" * 55)
    
    for info in grammar_info_list:
        print(f"{info['type']:9} | {info['label']:20} | {info['affix']:6} | {info['example']}")


def estimate_collisions(generator):
    """Оценка вероятности коллизий"""
    print("\n--- ОЦЕНКА ВЕРОЯТНОСТИ КОЛЛИЗИЙ ---")
    
    try:
        count_input = input("Введите количество слов для оценки (или нажмите Enter для 1000000): ").strip()
        if count_input:
            word_count = int(count_input)
        else:
            word_count = 1000000
        
        prob = generator.get_collision_probability(word_count)
        
        print(f"\nРезультаты оценки:")
        print(f"Количество слов: {word_count:,}")
        print(f"Вероятность коллизии: {prob:.10f}")
        print(f"Вероятность коллизии: {prob * 100:.6f}%")
        
        if prob < 0.0001:
            print("✅ Вероятность коллизии очень низкая")
        elif prob < 0.01:
            print("✅ Вероятность коллизии низкая")
        elif prob < 0.1:
            print("⚠️  Вероятность коллизии умеренная")
        else:
            print("❌ Вероятность коллизии высокая")
            
    except ValueError:
        print("Ошибка: введите корректное число.")
    except Exception as e:
        print(f"Ошибка при оценке коллизий: {e}")


def run_test_examples(generator):
    """Запуск тестовых примеров"""
    print("\n--- ТЕСТОВЫЕ ПРИМЕРЫ ---")
    
    # Добавлены примеры с короткими основами (2 буквы, 1 слог)
    test_words = [
        "happy", "running", "play", "quickly", "eating",
        "abpi", "baye", "comu", "deyepi", "fiyemu",  # Короткие основы из 2 букв
        "happyye", "happymu", "ab", "ba", "pi",  # Очень короткие слова
        "totalayepi", "totalaye", "aketotalaye", 
        "tototalaye",  # с приставкой to
        "hatotalaye",  # с приставкой ha (прошедшее время)
        "aketotalaye", # с приставкой ake (настоящее время)  
        "katotalaye",  # с приставкой ka (будущее время)
        "tatotalaye",  # с приставкой ta (отсутствие)
        "tetotalaye",  # с приставкой te (неопределенность)
        "aketotetalaniye"  # сложная конструкция
    ]
    
    print("Слово -> Время -> Модальности -> Суффикс -> Основа -> Полный ID -> Восстановлено -> Статус")
    print("-" * 100)
    
    for word in test_words:
        try:
            grammar_info = generator.detect_word_grammar(word)
            time = grammar_info['time_prefix']['prefix'] if grammar_info['time_prefix'] else 'нет'
            modalities = '/'.join([m['prefix'] for m in grammar_info['modality_prefixes']]) or 'нет'
            suffix = grammar_info['suffix']['suffix'] if grammar_info['suffix'] else 'нет'
            stem = grammar_info['stem']
            
            word_id = generator.word_to_id(word, '-', True, True)
            reconstructed, reconstructed_info = generator.id_to_word(word_id, '-', True, True)
            
            status = "✅" if word.lower() == reconstructed.lower() else "❌"
            
            print(f"{status} {word:20} -> {time:6} -> {modalities:11} -> {suffix:7} -> {stem:8} -> {word_id:15} -> {reconstructed:20}")
        except Exception as e:
            print(f"❌ {word:20} -> ОШИБКА: {e}")


def show_about():
    """Информация о программе"""
    print("\n--- О ПРОГРАММЕ ---")
    print("Генератор уникальных ID для слов")
    print("Версия 9.1 - С поддержкой коротких основ (2 буквы, 1 слог)")
    print("\nПорядок распознавания аффиксов:")
    print("1. Временные приставки: ha, ake, ka")
    print("2. Модальные приставки: to, te, ta (может быть несколько)")
    print("3. Суффиксы части речи: pi, ye, mu, yepi, yemu")
    print("\nГрамматические приставки:")
    print("- ha: Прошедшее время") 
    print("- ake: Настоящее время")
    print("- ka: Будущее время")
    print("- to: Абсолютизм/Совершенный вид")
    print("- ta: Полное отсутствие")
    print("- te: Неопределённость")
    print("\nГрамматические суффиксы:")
    print("- pi: Прилагательное")
    print("- yepi: Причастие")
    print("- ye: Глагол")
    print("- mu: Наречие")
    print("- yemu: Деепричастие")
    print("\nОСОБЕННОСТИ ВЕРСИИ 9.1:")
    print("- Основа может состоять из 2 букв (1 слог)")
    print("- Минимальный размер основы: 2 буквы + 1 гласная")
    print("- Поддержка очень коротких слов (ab, ba, pi и т.д.)")
    print("- Все остальные функции сохранены")


def interactive_mode():
    """Интерактивный режим работы с генератором"""
    generator = WordIDGenerator()
    
    print("Добро пожаловать в генератор уникальных ID для слов!")
    print("Версия 9.1 - С поддержкой коротких основ (2 буквы, 1 слог)")
    
    while True:
        display_menu()
        choice = input("Выберите действие (0-8): ").strip()
        
        if choice == '0':
            print("Выход из программы. До свидания!")
            break
        elif choice == '1':
            encode_word(generator)
        elif choice == '2':
            decode_id(generator)
        elif choice == '3':
            analyze_grammar(generator)
        elif choice == '4':
            show_grammar_affixes(generator)
        elif choice == '5':
            generator.print_stats()
        elif choice == '6':
            estimate_collisions(generator)
        elif choice == '7':
            run_test_examples(generator)
        elif choice == '8':
            show_about()
        else:
            print("Неверный выбор. Пожалуйста, введите число от 0 до 8.")


# Запуск программы
if __name__ == "__main__":
    interactive_mode()
