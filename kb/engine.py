"""Поиск и прямой вывод. Сопоставление и правила выполняются запросами SQL."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kb.norm import code_key, normalize

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SQL = ROOT / "sql"
DB_PATH = DATA / "additives.db"
STAMP = DATA / ".db-stamp"

LEVEL_RANK = {"info": 1, "check": 2, "warn": 3, "forbid": 4}

CATEGORIES = [
    "",
    "напитки",
    "кондитерские изделия",
    "мясная продукция",
    "детское питание",
    "общая пищевая продукция",
]

_SCORED = (SQL / "scored.sql").read_text(encoding="utf-8")
_COUNT_SQL = f"WITH scored AS (\n{_SCORED}\n)\nSELECT COUNT(*) AS total FROM scored WHERE score > 0"
_PAGE_SQL = (
    f"WITH scored AS (\n{_SCORED}\n)\n"
    "SELECT * FROM scored WHERE score > 0 ORDER BY score DESC, code LIMIT :limit OFFSET :offset"
)
_CONSULT = (SQL / "consult.sql").read_text(encoding="utf-8")
_RULE_SQL, _COMPOSITION_SQL = _CONSULT.split("-- @@composition", 1)
_RULE_SQL = _RULE_SQL.split("-- @@additive", 1)[1]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_db() -> None:
    seed = SQL / "seed.sql"
    schema = SQL / "schema.sql"
    stamp = f"{seed.stat().st_mtime:.6f}:{schema.stat().st_mtime:.6f}"
    if DB_PATH.exists() and STAMP.exists() and STAMP.read_text(encoding="utf-8") == stamp:
        return
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema.read_text(encoding="utf-8"))
    conn.executescript(seed.read_text(encoding="utf-8"))
    conn.close()
    STAMP.write_text(stamp, encoding="utf-8")


def _split_rows(conn: sqlite3.Connection, table: str, column: str, ids: list[int], order: str) -> dict:
    if not ids:
        return {}
    marks = ",".join("?" * len(ids))
    found: dict[int, list] = {}
    query = f"SELECT additive_id, {column} AS value FROM {table} WHERE additive_id IN ({marks}) ORDER BY {order}"
    for row in conn.execute(query, ids):
        found.setdefault(row["additive_id"], []).append(row["value"])
    return found


def _hydrate(conn: sqlite3.Connection, rows: list) -> list[dict]:
    ids = [row["id"] for row in rows]
    aliases = _split_rows(conn, "additive_alias", "alias", ids, "id")
    functions = _split_rows(conn, "additive_function", "name_ru", ids, "ord")
    annexes = _split_rows(conn, "additive_annex", "annex", ids, "ord")
    warnings = _split_rows(conn, "additive_warning", "warning", ids, "warning")
    items = []
    for row in rows:
        item = {
            "code": row["code"],
            "name_ru": row["name_ru"],
            "name_en": row["name_en"],
            "aliases": aliases.get(row["id"], []),
            "group": row["group_code"],
            "functions": functions.get(row["id"], []),
            "status": row["status"],
            "annexes": annexes.get(row["id"], []),
            "changed_2024": bool(row["changed_2024"]),
            "warnings": warnings.get(row["id"], []),
            "origin": row["origin"],
            "summary": row["summary"],
            "eu_note": row["eu_note"],
            "slug": row["slug"],
        }
        if "score" in row.keys():
            item["score"] = row["score"]
            item["reason"] = row["reason"]
        items.append(item)
    return items


def _one(conn: sqlite3.Connection, where: str, value: str):
    row = conn.execute(f"SELECT * FROM additive WHERE {where} = ?", (value,)).fetchone()
    if row is None:
        return None
    return _hydrate(conn, [row])[0]


def get_additive(code: str):
    key = code_key(code)
    conn = _connect()
    try:
        return _one(conn, "code", key)
    finally:
        conn.close()


def get_by_slug(slug: str):
    conn = _connect()
    try:
        return _one(conn, "slug", (slug or "").strip().lower())
    finally:
        conn.close()


def search(query: str = "", group: str = "", status: str = "", page: int = 1, per_page: int = 8):
    needle = normalize(query)
    params = {
        "needle": needle,
        "compact": needle.replace(" ", ""),
        "group_code": group or "",
        "status": status or "",
    }
    conn = _connect()
    try:
        total = conn.execute(_COUNT_SQL, params).fetchone()["total"]
        pages = max(1, (total + per_page - 1) // per_page)
        page = min(max(page, 1), pages)
        rows = conn.execute(
            _PAGE_SQL,
            {**params, "limit": per_page, "offset": (page - 1) * per_page},
        ).fetchall()
        items = _hydrate(conn, rows)
    finally:
        conn.close()
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
    }


def parse_codes(raw: str) -> list[str]:
    chunks = raw.replace(";", ",").replace("\n", ",").split(",")
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def _parse_share(value: str):
    text = (value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def consult(raw_codes: str, category: str = "", polyol_share: str = ""):
    share = _parse_share(polyol_share)
    selected = []
    unknown = []
    seen = set()
    for raw in parse_codes(raw_codes):
        item = get_additive(raw)
        if item is None:
            unknown.append(raw.strip())
        elif item["code"] not in seen:
            seen.add(item["code"])
            selected.append(item)

    params = {
        "share_set": 0 if share is None else 1,
        "share": -1.0 if share is None else share,
        "category": category or "",
    }
    conn = _connect()
    try:
        conn.execute("CREATE TEMP TABLE ask(code TEXT PRIMARY KEY)")
        conn.executemany("INSERT INTO ask(code) VALUES (?)", [(item["code"],) for item in selected])
        fired_rows = list(conn.execute(_RULE_SQL, params)) + list(conn.execute(_COMPOSITION_SQL, params))
    finally:
        conn.close()

    fired = [
        {
            "id": row["id"],
            "title": row["title"],
            "level": row["level"],
            "code": row["code"],
            "text": row["text"],
        }
        for row in fired_rows
    ]
    for raw in unknown:
        fired.append(
            {
                "id": "R00",
                "title": "Индекса нет в прототипе",
                "level": "check",
                "code": raw,
                "text": (
                    f"«{raw}» нет среди загруженных фактов. Приложение 2 — закрытый перечень: "
                    "добавку вне него не применяют, пока её туда не включат. Сначала проверьте написание индекса."
                ),
            }
        )
    fired.sort(key=lambda row: (-LEVEL_RANK[row["level"]], row["id"], row.get("code") or ""))
    worst = max((LEVEL_RANK[row["level"]] for row in fired), default=0)
    return {
        "selected": selected,
        "unknown": unknown,
        "fired": fired,
        "verdict": _verdict(worst, selected, unknown),
        "category": category,
        "polyol_share": share,
    }


def _verdict(worst: int, selected, unknown) -> dict:
    if not selected and not unknown:
        return {"level": "check", "title": "Состав пуст", "text": "Введите хотя бы один индекс, например E330 или E102, E211."}
    if worst >= LEVEL_RANK["forbid"]:
        return {
            "level": "forbid",
            "title": "Есть исключённая добавка",
            "text": "Пока в составе остаётся добавка вне приложения 2, прототип не считает рецептуру допустимой для производства в ЕАЭС.",
        }
    if worst >= LEVEL_RANK["warn"]:
        return {
            "level": "warn",
            "title": "Нужны надписи или технологическая проверка",
            "text": "Запрета по перечню нет. Выпуск упирается в маркировку или в условие, которое перечислено ниже.",
        }
    if worst >= LEVEL_RANK["check"] or unknown:
        return {
            "level": "check",
            "title": "Автоматического запрета нет",
            "text": "Остались вопросы, которые прототип сознательно не закрывает: норма конкретного продукта или незнакомый индекс.",
        }
    return {
        "level": "info",
        "title": "По правилам прототипа запрета нет",
        "text": "Сработавшие сведения не мешают применению в принципе. Максимальный уровень для вида продукции всё равно берут из указанного приложения регламента.",
    }


ensure_db()
_labels = _connect()
try:
    GROUP_LABELS = {
        row["code"]: row["name_ru"]
        for row in _labels.execute("SELECT code, name_ru FROM func_group ORDER BY ord")
    }
finally:
    _labels.close()
