# Translation Engine Data

Репозиторий исходных словарных и фразовых данных для `translation_engine`. Python-скрипты преобразуют источники для пары English–Russian в JSONL, используемый движком перевода.

## Возможности

- Хранение исходного TEI-словаря, набора фраз TSV и таблицы частот.
- Преобразование словарных статей TEI в `dictionary.jsonl`.
- Преобразование параллельных фраз TSV в `phrases.jsonl`.
- Очистка текста, удаление дубликатов и расчёт относительной частотности.
- Архив `zip/en-ru.zip` для загрузки подготовленного набора средствами `translation_engine`.

## Стек

- TEI XML
- TSV и CSV
- JSON и JSONL
- Python 3, стандартная библиотека

## Быстрый старт

Скрипты принимают необязательные пути к входному и выходному файлам. Без аргументов они используют файлы из `data/` и записывают результат в `en-ru/`.

```bash
git clone https://github.com/VernaculusF/translation-engine-data.git
cd translation-engine-data
python3 scripts/tei_to_jsonl.py
python3 scripts/tsv_phrases_to_jsonl.py
```

Явное указание путей:

```bash
python3 scripts/tei_to_jsonl.py data/eng-rus.tei en-ru/dictionary.jsonl data/unigram_freq.csv
python3 scripts/tsv_phrases_to_jsonl.py "data/phrases - 2025-11-04.tsv" en-ru/phrases.jsonl
```

Подготовленный архив загружается из проекта `translation_engine` командой:

```bash
dart run bin/translate_engine.dart db --lang=en-ru
```

## Структура проекта

```text
data/                         исходные TEI, TSV и CSV
scripts/tei_to_jsonl.py       конвертация словаря в JSONL
scripts/tsv_phrases_to_jsonl.py  конвертация фраз в JSONL
zip/en-ru.zip                 подготовленный архив English–Russian
index.json                    индекс доступных наборов
schema.yaml                   описание формата данных
DATA_PREP.md                  сведения о подготовке данных
data.md                       дополнительные сведения об источниках
```

## Качество данных

Данные собраны и преобразованы из внешних источников. Репозиторий не гарантирует полноту, точность, актуальность переводов, отсутствие дубликатов или пригодность данных для конкретной задачи. Перед использованием в рабочей системе данные следует проверять с учётом требований проекта и лицензий первичных источников.

## Лицензия

MIT. Условия приведены в файле `LICENSE`.
