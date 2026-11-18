# -*- coding: utf-8 -*-
"""Собирает sql/seed.sql из фактов и правил. Рабочая база читает уже этот SQL."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kb.norm import make_slug, normalize

DATA = ROOT / "data"
OUT = ROOT / "sql" / "seed.sql"


def q(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    text = str(value).replace("'", "''")
    return "'" + text + "'"


def load(name: str):
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


def assign_slugs(items: list) -> None:
    used = set()
    for item in items:
        slug = make_slug(item["name_ru"])
        if slug in used:
            slug = f"{slug}-{item['code'].lower()}"
        used.add(slug)
        item["slug"] = slug


def rule_columns(rule: dict):
    cond = rule["when"]
    polyol_mode = None
    polyol_value = None
    if cond.get("polyol_unset"):
        polyol_mode = "unset"
    elif "polyol_share_gt" in cond:
        polyol_mode = "gt"
        polyol_value = cond["polyol_share_gt"]
    elif "polyol_share_le" in cond:
        polyol_mode = "le"
        polyol_value = cond["polyol_share_le"]
    changed = None
    if "changed_2024" in cond:
        changed = 1 if cond["changed_2024"] else 0
    return {
        "need_status": cond.get("status"),
        "need_warning": cond.get("warning"),
        "need_code": cond.get("code"),
        "need_changed": changed,
        "polyol_mode": polyol_mode,
        "polyol_value": polyol_value,
        "need_category": cond.get("category"),
        "exclude": list(cond.get("category_not_in") or []),
        "requires": list(cond.get("requires_codes") or []),
    }


def main() -> None:
    additives = load("additives.json")
    rules = load("rules.json")
    ontology = load("ontology.json")
    assign_slugs(additives)
    lines = [
        "-- Наполнение базы знаний. Файл получен из data/additives.json и data/rules.json.",
        "-- Загрузка: sqlite3 data/additives.db < sql/schema.sql",
        "--           sqlite3 data/additives.db < sql/seed.sql",
        "BEGIN;",
    ]
    for ord_, (code, name) in enumerate(ontology["groups"].items(), start=1):
        lines.append(
            f"INSERT INTO func_group(code, name_ru, ord) VALUES ({q(code)}, {q(name)}, {ord_});"
        )
    alias_id = 1
    function_id = 1
    annex_id = 1
    for additive_id, item in enumerate(additives, start=1):
        lines.append(
            "INSERT INTO additive(id, code, slug, name_ru, name_en, group_code, status, origin, "
            "summary, eu_note, changed_2024, name_ru_norm, name_en_norm, summary_norm) VALUES ("
            + ", ".join(
                [
                    str(additive_id),
                    q(item["code"]),
                    q(item["slug"]),
                    q(item["name_ru"]),
                    q(item["name_en"]),
                    q(item["group"]),
                    q(item["status"]),
                    q(item["origin"]),
                    q(item["summary"]),
                    q(item["eu_note"]),
                    "1" if item["changed_2024"] else "0",
                    q(normalize(item["name_ru"])),
                    q(normalize(item["name_en"])),
                    q(normalize(item["summary"])),
                ]
            )
            + ");"
        )
        for alias in item["aliases"]:
            lines.append(
                "INSERT INTO additive_alias(id, additive_id, alias, alias_norm) VALUES ("
                f"{alias_id}, {additive_id}, {q(alias)}, {q(normalize(alias))});"
            )
            alias_id += 1
        for ord_, function in enumerate(item["functions"], start=1):
            lines.append(
                "INSERT INTO additive_function(id, additive_id, name_ru, name_norm, ord) VALUES ("
                f"{function_id}, {additive_id}, {q(function)}, {q(normalize(function))}, {ord_});"
            )
            function_id += 1
        for ord_, annex in enumerate(item["annexes"], start=1):
            lines.append(
                "INSERT INTO additive_annex(id, additive_id, annex, ord) VALUES ("
                f"{annex_id}, {additive_id}, {q(annex)}, {ord_});"
            )
            annex_id += 1
        for warning in item["warnings"]:
            lines.append(
                "INSERT INTO additive_warning(additive_id, warning) VALUES ("
                f"{additive_id}, {q(warning)});"
            )
    for rule in rules:
        cols = rule_columns(rule)
        lines.append(
            "INSERT INTO rule(id, title, scope, level, body, need_status, need_warning, need_code, "
            "need_changed, polyol_mode, polyol_value, need_category) VALUES ("
            + ", ".join(
                [
                    q(rule["id"]),
                    q(rule["title"]),
                    q(rule["scope"]),
                    q(rule["level"]),
                    q(rule["text"]),
                    q(cols["need_status"]),
                    q(cols["need_warning"]),
                    q(cols["need_code"]),
                    q(cols["need_changed"]),
                    q(cols["polyol_mode"]),
                    q(cols["polyol_value"]),
                    q(cols["need_category"]),
                ]
            )
            + ");"
        )
        for category in cols["exclude"]:
            lines.append(
                "INSERT INTO rule_category_exclude(rule_id, category) VALUES ("
                f"{q(rule['id'])}, {q(category)});"
            )
        for code in cols["requires"]:
            lines.append(
                f"INSERT INTO rule_requires(rule_id, code) VALUES ({q(rule['id'])}, {q(code)});"
            )
    lines.append("COMMIT;")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{OUT} additives={len(additives)} rules={len(rules)}")


if __name__ == "__main__":
    main()
