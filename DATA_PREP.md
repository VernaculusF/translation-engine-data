# Руководство по данным (Translation Engine)

Документ описывает целевую структуру репозитория данных, форматы файлов и требования к исходникам для сборки и распространения двуязычных данных движка.

Структура репозитория (целевая)
- index.json                    # список языков и метаданные (уже есть)
- schema.yaml                   # подсказки по форматам (уже есть)
- {lang}/                       # папка на языковую пару (ISO 639‑1)
  - dictionary.jsonl            # словарь «слово→слово» по смыслам (по одному JSON‑объекту в строке)
  - phrases.jsonl               # многословные фразы/идиомы
  - grammar_rules.jsonl         # опционально: грамматические правила
  - word_order_rules.jsonl      # опционально: порядок слов
  - post_processing_rules.jsonl # опционально: пост‑обработка
  - dictionary.csv (необязательный seed‑файл)
  - phrases.csv    (необязательный seed‑файл)

Важно: команда ядра db ожидает URL вида {repo_root}/{lang}/dictionary.jsonl и {repo_root}/{lang}/phrases.jsonl. Не публикуйте конечные JSONL только под data/ — держите их в папках языковых пар на корне репозитория.

Dictionary.jsonl (по одному объекту на строку)
Обязательные поля:
- source_word: string (лемма на языке‑источнике)
- target_word: string (перевод на целевом языке)
- language_pair: string (например, "en-ru")

Рекомендуемые поля:
- part_of_speech: один из [noun, verb, adjective, adverb, pronoun, preposition, conjunction, interjection, article]
- sense_id: string (стабильный идентификатор смысла внутри headword)
- definition: string (краткое объяснение)
- domains: ["general", "it", "travel", ...]
- examples: ["пример употребления ..."]
- default_sense: boolean (дефолтный смысл)
- priority (или rank): integer (чем больше — тем предпочтительнее)
- frequency: integer 1..100 (см. нормализацию ниже)
- created_at, updated_at: unix epoch ms

Пример строки:
{"source_word":"go","target_word":"идти","language_pair":"en-ru","part_of_speech":"verb","sense_id":"go.mv.motion","definition":"move on foot","default_sense":true,"priority":80,"frequency":62,"created_at":1730600000000,"updated_at":1730600000000}

Phrases.jsonl (по одному объекту на строку)
Обязательные: source_phrase, target_phrase, language_pair
Опциональные: category, context, confidence(0..100), frequency(1..100)

Пример:
{"source_phrase":"good morning","target_phrase":"доброе утро","language_pair":"en-ru","category":"greetings","context":"neutral","confidence":95,"frequency":60}

Файлы правил (опционально)
- grammar_rules.jsonl: {rule_id, source_language, target_language, description, pattern, replacement, priority, conditions[], case_sensitive}
- word_order_rules.jsonl: {rule_id, source_language, target_language, description, source_order, target_order, pattern, reorder_template, priority, conditions[], case_sensitive}
- post_processing_rules.jsonl: {rule_id, description, pattern, replacement, priority, target_languages[], is_global, case_sensitive}

CSV‑исходники (допустимы как входы, не как конечные артефакты)
- dictionary.csv (seed): столбцы (в указанном порядке)
  - source_word, target_word, language_pair
  - опционально: part_of_speech, definition, priority/rank, default_sense(bool), frequency
- phrases.csv (seed): столбцы
  - source_phrase, target_phrase, language_pair
  - опционально: category, context, confidence, frequency

Английские униграммы (word,count) — реальные данные
- Формат: word,count (целые). Это монолингвальная частота употребления, годится как prior.
- Нормализация в оценку 1..100 для словаря:
  - log_count = ln(count + 1)
  - шкалирование min‑max или по квантилям → prior_src в [0..1]
  - frequency = round(1 + prior_src * 99)
  - альтернатива: бины по процентилям (топ 1%→95..100; топ 5%→80..94 и т.д.)
- Слияние: матч по source_word (лемма); при нескольких смыслах prior — лишь слабый tie‑break, выбор контролируется priority/default_sense.

Если частоты недоступны
- Присвоить внутри headword «лестницу» (ladder), напр. [80,60,50,40,30], используя детерминированные правила:
  - однословные цели > многословные
  - не транслитерация > транслитерация
  - не когнат > когнат
  - POS‑веса (служебные слова ниже)
- Небольшой стабильный offset по hash(source+target), чтобы избежать нестабильных ничьих; RNG не использовать.

Детерминированный выбор по контексту (для справки о рантайме)
- Порядок: Phrase → Frames/Collocations → Dictionary → Default sense → Copy/Translit(UNK)
- Окно контекста: [-2..+2], признаки: prev/next lemma/POS, предлог/частица, object_class
- Выбор мемоизируется по сигнатуре (lemma+prep+object_class+prev_pos+next_pos) с TTL

Именование файлов
- Папки языковых пар на корне: en-ru/, ru-en/ и т.д.
- Конечные файлы: dictionary.jsonl, phrases.jsonl (CLI ждёт именно такие имена)
- CSV seed‑ы можно держать рядом: en-ru/dictionary.csv, en-ru/phrases.csv (опционально)

Очистка/миграция
- Удалите/переместите устаревшие data/* (dictionary.jsonl, phrases.jsonl, *_rules.jsonl) в {lang}/
- index.json и schema.yaml остаются на корне.

Открытые источники (реально доступные)
- Частоты (EN):
  - wordfreq: https://github.com/rspeer/wordfreq (частоты по языкам, готовые списки)
  - Google Ngrams: https://books.google.com/ngrams (монолингвальные счётчики)
  - SUBTLEX‑US/UK (требует отсылки к публикации)
- Двуязычные пары:
  - Wiktionary (дампы): https://dumps.wikimedia.org/ (извлечь парные переводы)
  - Tatoeba: https://tatoeba.org/ (CC BY, предложения с переводами)
  - OPUS: https://opus.nlpl.eu/ (параллельные корпуса; требуется фильтрация)
  - OpenRussian: https://en.openrussian.org/ (RU‑лексикон, CC BY‑SA)

Спецификация питон‑скрипта импорта (outline)
- Входы:
  - en_unigrams.csv: word,count (UTF‑8)
  - dictionary_seed.csv: source_word,target_word,language_pair[,part_of_speech,definition,priority,default_sense]
  - phrases_seed.csv (опционально)
- Шаги:
  1) Загрузить униграммы → prior_src[word] = score_1_100 (лог + min‑max/перцентили)
  2) Читать dictionary_seed → объект; если есть POS/default_sense/priority — использовать; иначе вывести priority по ladder‑правилам
  3) frequency = prior_src.get(lemma, None) или bucket_from_ladder(priority)
  4) Добавить timestamps, sense_id (детерминированный hash(source+target+pos)), нормализовать Unicode NFC
  5) Записать JSONL в {lang}/dictionary.jsonl (атомарно tmp+rename)
  6) Аналогично для фраз → {lang}/phrases.jsonl
- Валидация:
  - Проверить обязательные поля; соответствие language_pair папке; отсутствие дублей (source_word+language_pair)

Примечания
- Держите строки JSONL разумного размера; при больших объёмах — шардинг по префиксу (A.jsonl, B.jsonl, …) + manifest.
- CLI db скачивает {repo_root}/{lang}/dictionary.jsonl и {repo_root}/{lang}/phrases.jsonl — проверьте URL после публикации.

---

Дополнение: заполнение поля frequency (1..100)
- Источник: достаточно монолингвальных частот языка-источника. Для пары en-ru — частоты английских слов (unigrams: word,count или Zipf). Эти частоты ранжируют source_word и служат prior для выбора перевода.
- Нормализация (вариант A — count):
  1) log_count = ln(count+1)
  2) min_max = (log_count - min_log) / (max_log - min_log)
  3) frequency = round(1 + min_max * 99)
- Нормализация (вариант B — Zipf из wordfreq): Zipf лежит примерно в [1..7]. frequency = round(1 + ((zipf-1) / 6) * 99).
- Предобработка ключа: lower → Unicode NFC → удалить диакритику (как в конвертере TEI) → обрезать пунктуацию/кавычки/длины дефисов. Лемматизация опциональна; если есть — применить (goes→go), иначе используйте вид из словаря.
- Многословные фразы: агрегируйте по словам источника: геом. среднее или min-компоненты. Рекомендация: frequency_phrase = round(0.9 * min(components)).
- Если частоты нет (OOV):
  1) Попробовать простую нормализацию (singular/plural, -ed/-ing);
  2) Fallback по «лестнице» смысла внутри headword (например: 80, 60, 50, 40, 30);
  3) POS-базовый дефолт (пример): noun=40, verb=45, adjective=35, adverb=35, pronoun=30; затем небольшой стабильный сдвиг ±2 по hash(source_word+target_word), чтобы избежать ничьих;
  4) Иначе поставить 20 как безопасный минимум.
- Стабильность: не пересчитывайте уже выданные значения без нужды; храните кэш частот и используйте его между релизами, чтобы приоритеты не «прыгали».
- Проверки качества: распределение значений по бинам; top‑N слов действительно самые частотные; отсутствие экстремумов (1 и 100) для середняков.
- Релевантность направлению: для en→ru используйте частоту английского source_word — этого достаточно; для ru→en — наоборот, частоты русского.

Минимальный псевдокод
```python
from math import log

# counts: dict[word] -> raw_count или zipf: dict[word] -> zipf_score

def to_frequency_from_count(count, min_log, max_log):
    x = log(count + 1.0)
    if max_log == min_log:
        return 50
    score = (x - min_log) / (max_log - min_log)
    return int(round(1 + score * 99))

def to_frequency_from_zipf(zipf):
    return int(round(1 + max(0.0, min(1.0, (zipf - 1.0) / 6.0)) * 99))
```

Примечание: отсутствие покрытия по части слов — норма. Используйте fallback‑стратегии выше; это не блокирует сборку словаря и обеспечивает детерминированность выбора.
