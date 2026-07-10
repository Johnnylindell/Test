#!/usr/bin/env python3
from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "content" / "articles" / "articles.json"
PRODUCTS = ROOT / "data" / "products.json"
STOP = {"bästa", "smart", "smarta", "hem", "för", "och", "med", "utan", "familj", "familjer", "barnfamilj", "guide", "så", "vad", "man", "att", "eller", "hemma"}


def words(text: str) -> list[str]:
    return re.findall(r"[a-zåäö0-9]+", text.lower())


def title_tokens(text: str) -> set[str]:
    return {word for word in words(text) if word not in STOP and len(word) > 2}


def article_word_count(article: dict) -> int:
    chunks = [article.get("title", ""), article.get("description", ""), article.get("intro", "")]
    chunks.extend(str(part) for section in article.get("sections", []) for part in section[:2])
    chunks.extend(str(item) for item in article.get("examples", []))
    return len(words(" ".join(chunks)))


def main() -> None:
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    products = json.loads(PRODUCTS.read_text(encoding="utf-8"))
    by_product = {item["id"]: item for item in products}

    duplicate_examples = Counter(
        " ".join(str(item).lower().split())
        for article in articles
        for item in article.get("examples", [])
        if str(item).strip()
    )
    duplicate_examples = {text: count for text, count in duplicate_examples.items() if count > 1}

    close_titles = []
    for left, right in itertools.combinations(articles, 2):
        a, b = title_tokens(left["title"]), title_tokens(right["title"])
        similarity = len(a & b) / max(1, len(a | b))
        if similarity >= 0.5:
            close_titles.append((similarity, left["slug"], right["slug"]))

    missing_models = []
    for article in articles:
        if article.get("category") != "köpguide":
            continue
        for product_id in article.get("products", []):
            product = by_product.get(product_id)
            if not product or not product.get("models"):
                missing_models.append((article["slug"], product_id))

    thin = sorted((article_word_count(article), article["slug"]) for article in articles if article_word_count(article) < 120)
    flagship = sum(article_word_count(article) >= 300 for article in articles)

    print(f"articles={len(articles)} flagship_300plus={flagship} thin_under_120={len(thin)}")
    print(f"duplicate_examples={len(duplicate_examples)} close_title_pairs={len(close_titles)} missing_model_links={len(missing_models)}")
    if close_titles:
        for similarity, left, right in sorted(close_titles, reverse=True)[:10]:
            print(f"title_overlap {similarity:.2f}: {left} <> {right}")
    if thin:
        print("thin_next:")
        for count, slug in thin[:10]:
            print(f"  {count:3d} {slug}")

    if duplicate_examples or missing_models:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
