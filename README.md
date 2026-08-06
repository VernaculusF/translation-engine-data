# Translation Engine Data

Source dictionary and phrase data for `translation_engine`. Python scripts convert English-Russian source datasets to the JSONL format consumed by the translation engine.

## Features

- Stores a source TEI dictionary, a TSV phrase dataset, and a frequency table.
- Converts TEI dictionary entries to `dictionary.jsonl`.
- Converts parallel TSV phrases to `phrases.jsonl`.
- Normalizes text, removes duplicates, and calculates relative frequency values.
- Provides `zip/en-ru.zip` for installation through `translation_engine`.

## Stack

- TEI XML
- TSV and CSV
- JSON and JSONL
- Python 3 standard library

## Quick start

The scripts accept optional input and output paths. Without arguments, they read source files from `data/` and write generated files to `en-ru/`.

```bash
git clone https://github.com/VernaculusF/translation-engine-data.git
cd translation-engine-data
python3 scripts/tei_to_jsonl.py
python3 scripts/tsv_phrases_to_jsonl.py
```

To specify paths explicitly:

```bash
python3 scripts/tei_to_jsonl.py data/eng-rus.tei en-ru/dictionary.jsonl data/unigram_freq.csv
python3 scripts/tsv_phrases_to_jsonl.py "data/phrases - 2025-11-04.tsv" en-ru/phrases.jsonl
```

The `translation_engine` project installs the prepared archive with:

```bash
dart run bin/translate_engine.dart db --lang=en-ru
```

## Project structure

```text
data/                            Source TEI, TSV, and CSV files
scripts/tei_to_jsonl.py          TEI dictionary converter
scripts/tsv_phrases_to_jsonl.py  TSV phrase converter
en-ru/                           Generated language-pair data
zip/en-ru.zip                    Prepared dataset archive
index.json                       Available dataset index
schema.yaml                      Data format schema
```

## Data quality

The data is collected and transformed from external sources. This repository does not guarantee completeness, translation accuracy, currentness, absence of duplicates, or suitability for a specific purpose. Validate the data and the licenses of its original sources before production use.

## License

MIT. See `LICENSE` for the full terms.
