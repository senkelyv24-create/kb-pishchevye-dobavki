"""Приведение запроса к одному виду перед сравнением в SQL."""


_FOLDS = (
    ("ё", "е"),
    ("е", "e"),
    ("а", "a"),
    ("о", "o"),
    ("р", "p"),
    ("с", "c"),
    ("х", "x"),
    ("у", "y"),
    ("к", "k"),
    ("м", "m"),
    ("т", "t"),
    ("н", "h"),
    ("в", "b"),
)

_SLUG = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def normalize(text: str) -> str:
    """Нижний регистр, «ё» → «е», латинские двойники кириллицы в индексе."""
    value = (text or "").strip().lower()
    for src, dst in _FOLDS:
        value = value.replace(src, dst)
    return " ".join(value.split())


def code_key(text: str) -> str:
    return normalize(text).replace(" ", "").upper().replace("Е", "E")


def make_slug(name: str) -> str:
    """Адрес страницы из названия: «Бензоат натрия» → benzoat-natriya."""
    source = (name or "").split(":")[0].strip().lower().replace("ё", "е")
    chars = []
    for char in source:
        if char in _SLUG:
            chars.append(_SLUG[char])
        elif char.isascii() and char.isalnum():
            chars.append(char)
        else:
            chars.append("-")
    return "-".join(part for part in "".join(chars).split("-") if part)
