-- Схема базы знаний по пищевым добавкам (SQLite).
-- Фрейм добавки — строка additive. Повторяющиеся слоты вынесены в отдельные таблицы.
-- Правило — строка rule: условие лежит в столбцах, текст вывода не зашит в программу.

PRAGMA foreign_keys = ON;

CREATE TABLE func_group (
    code TEXT PRIMARY KEY,
    name_ru TEXT NOT NULL,
    ord INTEGER NOT NULL
);

CREATE TABLE additive (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    name_ru TEXT NOT NULL,
    name_en TEXT NOT NULL,
    group_code TEXT NOT NULL REFERENCES func_group(code),
    status TEXT NOT NULL CHECK (status IN ('allowed', 'excluded')),
    origin TEXT NOT NULL,
    summary TEXT NOT NULL,
    eu_note TEXT NOT NULL,
    changed_2024 INTEGER NOT NULL CHECK (changed_2024 IN (0, 1)),
    name_ru_norm TEXT NOT NULL,
    name_en_norm TEXT NOT NULL,
    summary_norm TEXT NOT NULL
);

CREATE TABLE additive_alias (
    id INTEGER PRIMARY KEY,
    additive_id INTEGER NOT NULL REFERENCES additive(id),
    alias TEXT NOT NULL,
    alias_norm TEXT NOT NULL
);

CREATE TABLE additive_function (
    id INTEGER PRIMARY KEY,
    additive_id INTEGER NOT NULL REFERENCES additive(id),
    name_ru TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    ord INTEGER NOT NULL
);

CREATE TABLE additive_annex (
    id INTEGER PRIMARY KEY,
    additive_id INTEGER NOT NULL REFERENCES additive(id),
    annex TEXT NOT NULL,
    ord INTEGER NOT NULL
);

CREATE TABLE additive_warning (
    additive_id INTEGER NOT NULL REFERENCES additive(id),
    warning TEXT NOT NULL,
    PRIMARY KEY (additive_id, warning)
);

CREATE TABLE rule (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('additive', 'composition')),
    level TEXT NOT NULL CHECK (level IN ('info', 'check', 'warn', 'forbid')),
    body TEXT NOT NULL,
    need_status TEXT,
    need_warning TEXT,
    need_code TEXT,
    need_changed INTEGER,
    polyol_mode TEXT CHECK (polyol_mode IN ('unset', 'gt', 'le') OR polyol_mode IS NULL),
    polyol_value REAL,
    need_category TEXT
);

CREATE TABLE rule_category_exclude (
    rule_id TEXT NOT NULL REFERENCES rule(id),
    category TEXT NOT NULL,
    PRIMARY KEY (rule_id, category)
);

CREATE TABLE rule_requires (
    rule_id TEXT NOT NULL REFERENCES rule(id),
    code TEXT NOT NULL,
    PRIMARY KEY (rule_id, code)
);

CREATE INDEX idx_alias_norm ON additive_alias(alias_norm);
CREATE INDEX idx_alias_additive ON additive_alias(additive_id);
CREATE INDEX idx_function_additive ON additive_function(additive_id);
CREATE INDEX idx_warning_additive ON additive_warning(additive_id);
CREATE INDEX idx_additive_group ON additive(group_code);
CREATE INDEX idx_additive_status ON additive(status);
