# -*- coding: utf-8 -*-
"""Схемы для записки: архитектура и связи таблиц, в том же виде, что у образца."""

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"
FONT = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_B = Path(r"C:\Windows\Fonts\arialbd.ttf")

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
FILL = (242, 242, 242)
MAIN = (232, 232, 232)


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_B if bold else FONT), size)


def wrap(draw, text, fnt, width):
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = current + " " + word
            if draw.textlength(trial, font=fnt) <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def box(draw, xy, title, body, *, fill=FILL, title_size=30, body_size=24):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=18, fill=fill, outline=BLACK, width=3)
    tf = font(title_size, True)
    bf = font(body_size)
    title_lines = wrap(draw, title, tf, x2 - x1 - 36)
    y = y1 + 16
    for line in title_lines:
        w = draw.textlength(line, font=tf)
        draw.text(((x1 + x2 - w) / 2, y), line, font=tf, fill=BLACK)
        y += title_size + 8
    y += 6
    for line in wrap(draw, body, bf, x2 - x1 - 40):
        draw.text((x1 + 20, y), line, font=bf, fill=BLACK)
        y += body_size + 6


def arrow(draw, start, end, label=""):
    x1, y1 = start
    x2, y2 = end
    draw.line((x1, y1, x2, y2), fill=BLACK, width=3)
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 16
    head = [
        (x2, y2),
        (x2 - size * math.cos(angle - 0.4), y2 - size * math.sin(angle - 0.4)),
        (x2 - size * math.cos(angle + 0.4), y2 - size * math.sin(angle + 0.4)),
    ]
    draw.polygon(head, fill=BLACK)
    if label:
        fnt = font(22, True)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        tw = draw.textlength(label, font=fnt)
        draw.rectangle((mx - tw / 2 - 6, my - 16, mx + tw / 2 + 6, my + 16), fill=WHITE)
        draw.text((mx - tw / 2, my - 14), label, font=fnt, fill=BLACK)


def architecture():
    image = Image.new("RGB", (1700, 820), WHITE)
    draw = ImageDraw.Draw(image)
    box(
        draw,
        (40, 24, 1660, 190),
        "Веб-интерфейс (браузер): HTML, CSS",
        "Страницы: поиск добавок, карточка добавки, проверка состава.\n"
        "Поле запроса, разделы каталога, фильтр статуса, форма индексов.",
    )
    arrow(draw, (850, 190), (850, 250), "HTTP")
    box(
        draw,
        (40, 250, 1660, 430),
        "Сервер приложения: Flask (app.py)",
        "Адреса: /poisk, карточка по названию, /proverka.\n"
        "Страница не решает, какое правило истинно: она показывает ответ SQL.",
        fill=MAIN,
    )
    tops = [500, 500, 500, 500]
    lefts = [40, 455, 870, 1285]
    width = 375
    texts = [
        (
            "Хранение знаний",
            "SQLite: additives.db\n9 таблиц\n45 добавок\n13 правил",
        ),
        (
            "Обработка знаний",
            "sql/scored.sql — поиск\nsql/consult.sql — правила\nбез нейросети",
        ),
        (
            "Страницы",
            "templates/\nкарточка, список,\nитог и код правила",
        ),
        (
            "Правка знаний",
            "sql/seed.sql\nновая строка INSERT\nсборка tools/build_db.py",
        ),
    ]
    for left, (title, body) in zip(lefts, texts):
        box(draw, (left, 520, left + width, 780), title, body, title_size=26, body_size=22)
        arrow(draw, (left + width / 2, 520), (left + width / 2, 455))
    image.save(OUT / "21-architecture.png")


def model():
    image = Image.new("RGB", (1800, 1700), WHITE)
    draw = ImageDraw.Draw(image)
    box(
        draw,
        (30, 30, 390, 230),
        "additive_alias",
        "id (PK)\nadditive_id (FK)\nalias, alias_norm",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (30, 280, 390, 500),
        "additive_function",
        "id (PK)\nadditive_id (FK)\nname_ru, ord",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (30, 550, 390, 770),
        "additive_annex",
        "id (PK)\nadditive_id (FK)\nannex, ord",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (30, 820, 390, 1040),
        "additive_warning",
        "additive_id (FK)\nwarning\nпервичный ключ — пара",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (560, 250, 1120, 760),
        "additive",
        "id (PK)\ncode, slug\nname_ru, name_en\ngroup_code (FK)\n"
        "status, changed_2024\nsummary, eu_note\norigin",
        fill=MAIN,
        title_size=32,
        body_size=24,
    )
    box(
        draw,
        (1280, 360, 1760, 640),
        "func_group",
        "code (PK)\nname_ru\nord",
        fill=MAIN,
        title_size=28,
        body_size=24,
    )
    arrow(draw, (390, 130), (560, 340), "N : 1")
    arrow(draw, (390, 390), (560, 430), "N : 1")
    arrow(draw, (390, 660), (560, 560), "N : 1")
    arrow(draw, (390, 920), (560, 680), "N : 1")
    arrow(draw, (1120, 500), (1280, 500), "N : 1")

    box(
        draw,
        (80, 1100, 620, 1300),
        "rule_category_exclude",
        "rule_id (FK)\ncategory",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (1100, 1100, 1720, 1300),
        "rule_requires",
        "rule_id (FK)\ncode",
        title_size=26,
        body_size=22,
    )
    box(
        draw,
        (560, 1380, 1240, 1640),
        "rule",
        "id (PK)\nscope, level, body\nneed_status, need_warning\n"
        "need_code, need_category\npolyol_mode, polyol_value",
        fill=MAIN,
        title_size=30,
        body_size=22,
    )
    arrow(draw, (350, 1300), (720, 1380), "N : 1")
    arrow(draw, (1410, 1300), (1080, 1380), "N : 1")
    note = "Стрелка идёт от таблицы с внешним ключом (FK) к таблице, на которую он ссылается (PK)."
    fnt = font(22)
    draw.text((30, 1660), note, font=fnt, fill=BLACK)
    image.save(OUT / "22-model.png")


if __name__ == "__main__":
    architecture()
    model()
    print(OUT / "21-architecture.png")
    print(OUT / "22-model.png")
