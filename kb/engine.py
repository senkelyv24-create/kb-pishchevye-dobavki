"""Загрузка фактов и прямой вывод по правилам базы знаний."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

LEVEL_RANK = {"info": 1, "check": 2, "warn": 3, "forbid": 4}

GROUP_LABELS = {
    "color": "Красители",
    "preservative": "Консерванты",
    "antioxidant": "Антиокислители",
    "acid": "Регуляторы кислотности",
    "sweetener": "Подсластители",
    "texture": "Эмульгаторы и загустители",
    "flavor": "Усилители вкуса",
}

STATUS_LABELS = {
    "allowed": "В перечне ЕАЭС",
    "excluded": "Исключена в 2024",
}

CATEGORIES = [
    "",
    "напитки",
    "кондитерские изделия",
    "мясная продукция",
    "детское питание",
    "общая пищевая продукция",
]


def _load(name: str):
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


_TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def make_slug(name: str) -> str:
    """Адрес страницы из названия: «Бензоат натрия» → benzoat-natriya."""
    source = (name or "").split(":")[0].strip().lower().replace("ё", "е")
    chars = []
    for char in source:
        if char in _TRANSLIT:
            chars.append(_TRANSLIT[char])
        elif char.isascii() and char.isalnum():
            chars.append(char)
        else:
            chars.append("-")
    return "-".join(part for part in "".join(chars).split("-") if part)


def _assign_slugs(items: list) -> None:
    used = set()
    for item in items:
        slug = make_slug(item["name_ru"])
        if slug in used:
            slug = f"{slug}-{item['code'].lower()}"
        used.add(slug)
        item["slug"] = slug


ADDITIVES = _load("additives.json")
RULES = _load("rules.json")
ONTOLOGY = _load("ontology.json")
_assign_slugs(ADDITIVES)
BY_CODE = {item["code"].upper(): item for item in ADDITIVES}
BY_SLUG = {item["slug"]: item for item in ADDITIVES}


def normalize(text: str) -> str:
    value = (text or "").strip().lower().replace("ё", "е")
    for src, dst in (("е", "e"), ("а", "a"), ("о", "o"), ("р", "p"), ("с", "c"), ("х", "x"), ("у", "y"), ("к", "k"), ("м", "m"), ("т", "t"), ("н", "h"), ("в", "b")):
        value = value.replace(src, dst)
    return " ".join(value.split())


def code_key(text: str) -> str:
    return normalize(text).replace(" ", "").upper().replace("Е", "E")


def get_additive(code: str):
    key = code_key(code)
    if key in BY_CODE:
        return BY_CODE[key]
    return None


def get_by_slug(slug: str):
    return BY_SLUG.get((slug or "").strip().lower())


def search(query: str = "", group: str = "", status: str = "", page: int = 1, per_page: int = 8):
    needle = normalize(query)
    compact = needle.replace(" ", "")
    found = []
    for item in ADDITIVES:
        if group and item["group"] != group:
            continue
        if status == "excluded" and item["status"] != "excluded":
            continue
        if status == "allowed" and item["status"] != "allowed":
            continue
        if status == "warning" and not item["warnings"]:
            continue
        if status == "changed" and not item["changed_2024"]:
            continue
        score, reason = _score(item, needle, compact)
        if needle and score <= 0:
            continue
        if not needle:
            score, reason = 1, "раздел каталога"
        found.append({**item, "score": score, "reason": reason})
    found.sort(key=lambda row: (-row["score"], row["code"]))
    total = len(found)
    pages = max(1, (total + per_page - 1) // per_page)
    page = min(max(page, 1), pages)
    start = (page - 1) * per_page
    return {
        "items": found[start : start + per_page],
        "total": total,
        "page": page,
        "pages": pages,
        "per_page": per_page,
    }


def _score(item: dict, needle: str, compact: str) -> tuple[int, str]:
    if not needle:
        return 0, ""
    code = item["code"].lower()
    code_compact = code.replace("-", "")
    names = [normalize(item["name_ru"]), normalize(item["name_en"])]
    aliases = [normalize(alias) for alias in item["aliases"]]
    functions = [normalize(fn) for fn in item["functions"]]
    if compact in {code, code_compact, code.replace("e", "")}:
        return 100, "точный индекс"
    if compact.startswith("e") and code.startswith(compact):
        return 70, "индекс начинается с запроса"
    if any(needle == alias for alias in aliases):
        return 90, "совпало дополнительное имя"
    if any(needle == name for name in names):
        return 85, "совпало наименование"
    if any(needle in name for name in names):
        return 55, "часть наименования"
    if any(needle in alias or alias in needle for alias in aliases):
        return 50, "близкое имя"
    if any(needle in fn for fn in functions):
        return 30, "технологическая функция"
    if needle in normalize(item["summary"]):
        return 15, "слово из описания"
    return 0, ""


def parse_codes(raw: str) -> list[str]:
    chunks = raw.replace(";", ",").replace("\n", ",").split(",")
    codes = []
    for chunk in chunks:
        piece = chunk.strip()
        if piece:
            codes.append(piece)
    return codes


def consult(raw_codes: str, category: str = "", polyol_share: str = ""):
    share = _parse_share(polyol_share)
    selected = []
    unknown = []
    for raw in parse_codes(raw_codes):
        item = get_additive(raw)
        if item is None:
            unknown.append(raw.strip())
        elif item["code"] not in {row["code"] for row in selected}:
            selected.append(item)

    fired = []
    seen = set()
    for rule in RULES:
        if rule["scope"] == "composition":
            if _when(rule["when"], None, selected, category, share):
                key = rule["id"]
                if key not in seen:
                    seen.add(key)
                    fired.append(_hit(rule, None))
            continue
        for item in selected:
            if _when(rule["when"], item, selected, category, share):
                key = (rule["id"], item["code"])
                if key not in seen:
                    seen.add(key)
                    fired.append(_hit(rule, item))

    for raw in unknown:
        fired.append(
            {
                "id": "R00",
                "title": "Индекса нет в прототипе",
                "level": "check",
                "code": raw,
                "text": f"«{raw}» нет среди загруженных фактов. Приложение 2 — закрытый перечень: добавку вне него не применяют, пока её туда не включат. Сначала проверьте написание индекса.",
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


def _parse_share(value: str):
    text = (value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _when(cond: dict, item, selected, category: str, share) -> bool:
    if "requires_codes" in cond:
        have = {row["code"] for row in selected}
        if not set(cond["requires_codes"]).issubset(have):
            return False
    if item is not None:
        if "status" in cond and item["status"] != cond["status"]:
            return False
        if "warning" in cond and cond["warning"] not in item["warnings"]:
            return False
        if "code" in cond and item["code"] != cond["code"]:
            return False
        if "changed_2024" in cond and bool(item["changed_2024"]) != bool(cond["changed_2024"]):
            return False
        if "polyol_unset" in cond and share is not None:
            return False
        if "polyol_share_gt" in cond and (share is None or share <= cond["polyol_share_gt"]):
            return False
        if "polyol_share_le" in cond and (share is None or share > cond["polyol_share_le"]):
            return False
    if "category" in cond and category != cond["category"]:
        return False
    if "category_not_in" in cond and category in cond["category_not_in"]:
        return False
    return True


def _hit(rule: dict, item) -> dict:
    return {
        "id": rule["id"],
        "title": rule["title"],
        "level": rule["level"],
        "code": None if item is None else item["code"],
        "text": rule["text"],
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
