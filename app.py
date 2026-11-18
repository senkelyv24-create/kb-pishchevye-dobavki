"""Прототип базы знаний по пищевым добавкам."""

from flask import Flask, abort, redirect, render_template, request, url_for

from kb.engine import CATEGORIES, GROUP_LABELS, consult, get_additive, get_by_slug, search

app = Flask(__name__)

FEATURED = ["E330", "E621", "E171", "E960", "E102", "E202", "E500", "E211"]

STATUS_LINKS = [
    ("", "Все статусы"),
    ("allowed", "В перечне"),
    ("warning", "С надписью"),
    ("excluded", "Исключены в 2024"),
    ("changed", "Изменены в 2024"),
]


@app.context_processor
def inject_nav():
    return {
        "groups": GROUP_LABELS,
        "status_links": STATUS_LINKS,
        "categories": CATEGORIES,
        "featured": [get_additive(code) for code in FEATURED],
    }


@app.get("/")
def root():
    return redirect(url_for("index"))


@app.get("/poisk")
def index():
    query = request.args.get("q", "")
    group = request.args.get("group", "")
    status = request.args.get("status", "")
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    result = search(query, group, status, page)
    return render_template(
        "index.html",
        query=query,
        group=group,
        status=status,
        result=result,
    )


@app.get("/a/<code>")
def detail_by_code(code: str):
    item = get_additive(code)
    if item is None:
        abort(404)
    return redirect(url_for("detail", slug=item["slug"]))


@app.get("/<slug>")
def detail(slug: str):
    item = get_by_slug(slug)
    if item is None:
        abort(404)
    related = search(item["functions"][0], item["group"], "", 1, 5)["items"]
    related = [row for row in related if row["code"] != item["code"]][:4]
    return render_template("detail.html", item=item, related=related)


@app.route("/check", methods=["GET", "POST"])
@app.route("/proverka", methods=["GET", "POST"])
def check():
    source = request.form if request.method == "POST" else request.args
    raw = source.get("codes", "")
    category = source.get("category", "")
    share = source.get("polyol", "")
    report = consult(raw, category, share) if raw else None
    return render_template(
        "check.html",
        raw=raw,
        category=category,
        share=share,
        report=report,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
