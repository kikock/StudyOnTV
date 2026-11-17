#!/usr/bin/env python3
"""从 cn-math-taxonomy 仓库生成 StudyOnTV v2 格式的可导入题库文件。"""

import base64
import collections
import json
import os
import sys
from pathlib import Path

# 学科前缀与英文文件名映射
SUBJECT_MAP = {
    "cnm": ("数学", "math"),
    "cne": ("英语", "english"),
    "cnc": ("语文", "chinese"),
    "cnp": ("物理", "physics"),
    "cnk": ("化学", "chemistry"),
    "cnb": ("生物", "biology"),
    "cnh": ("历史", "history"),
    "cng": ("地理", "geography"),
    "cnd": ("道法", "ethics"),
    "cns": ("科学", "science"),
}

GRADE_MAP = {
    1: "一年级", 2: "二年级", 3: "三年级", 4: "四年级", 5: "五年级", 6: "六年级",
    7: "七年级", 8: "八年级", 9: "九年级", 10: "高一", 11: "高二", 12: "高三",
    13: "高中", 14: "高中", 15: "高中", 16: "高中",
}

DIFF_MAP = {"basic": 1, "standard": 2, "challenge": 3, "advanced": 4}


def convert_question(q: dict, topics: dict) -> tuple[str, dict | None]:
    """将单道 cn-math-taxonomy 题目转换为 StudyOnTV v2 格式。"""
    qid = q["id"]
    prefix = qid.split("_")[0]
    subj_name, slug = SUBJECT_MAP.get(prefix, ("常识", "general"))
    topic = topics.get(q.get("topicId", ""), {})
    level = GRADE_MAP.get(topic.get("grade"), "")
    prompt = (q.get("prompt") or "").strip()
    if not prompt or len(prompt) > 5000:
        return slug, None

    item: dict = {
        "id": qid,
        "q": prompt,
        "difficulty": DIFF_MAP.get(q.get("difficulty"), 2),
        "subject": subj_name,
        "bank": f"全学科题库-{subj_name}",
    }
    if level:
        item["level"] = level
    if q.get("explanation"):
        item["tip"] = q["explanation"].strip()
    if prefix == "cne":
        item["language"] = "en-US"

    fig = q.get("figure")
    if isinstance(fig, str) and fig.strip().startswith("<svg"):
        svg_b64 = base64.b64encode(fig.strip().encode("utf-8")).decode("ascii")
        data_uri = f"data:image/svg+xml;base64,{svg_b64}"
        if len(data_uri) <= 500_000:
            item["image"] = data_uri

    qtype = q.get("type")
    if qtype == "choice":
        choices = q.get("choices") or []
        opts = [str(c.get("text", "")).strip() for c in choices]
        ans_key = q.get("answer")
        k = next((i for i, c in enumerate(choices) if c.get("key") == ans_key), -1)
        if not (2 <= len(opts) <= 8) or any(not o for o in opts) or k < 0:
            return slug, None
        item["type"] = "single"
        item["a"] = opts
        item["k"] = k
    elif qtype in ("numeric", "short"):
        answers = []
        if q.get("answer") is not None and str(q["answer"]).strip():
            answers.append(str(q["answer"]).strip())
        for acc in q.get("accept") or []:
            s = str(acc).strip()
            if s and s not in answers:
                answers.append(s)
        if not answers:
            return slug, None
        item["type"] = "text"
        item["answers"] = answers
    elif qtype == "self":
        item["type"] = "subjective"
        item["modelAnswer"] = str(q.get("answer") or "").strip()
        item["rubric"] = str(q.get("explanation") or "").strip()
    else:
        return slug, None

    return slug, item


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    src_root = Path(sys.argv[1]) if len(sys.argv) > 1 else repo_root.parent / "cn-math-taxonomy"
    topics_path = src_root / "data" / "topics.json"
    questions_path = src_root / "data" / "questions.json"
    if not topics_path.exists() or not questions_path.exists():
        print(f"错误：未找到源题库文件：{src_root}", file=sys.stderr)
        return 1

    topics = {t["id"]: t for t in json.loads(topics_path.read_text(encoding="utf-8"))}
    questions = json.loads(questions_path.read_text(encoding="utf-8"))

    out_dir = repo_root / "data" / "banks" / "cn-math-taxonomy"
    out_dir.mkdir(parents=True, exist_ok=True)

    by_slug: dict[str, list[dict]] = collections.defaultdict(list)
    all_items: list[dict] = []
    seen_stems: set[str] = set()
    skipped_dup = 0
    skipped_invalid = 0

    for q in questions:
        slug, item = convert_question(q, topics)
        if item is None:
            skipped_invalid += 1
            continue
        stem_key = item["q"]
        if stem_key in seen_stems:
            skipped_dup += 1
            continue
        seen_stems.add(stem_key)
        by_slug[slug].append(item)
        all_items.append(item)

    lines = [
        "# cn-math-taxonomy 可导入题库（StudyOnTV v2 格式）",
        "",
        f"- 源题库总题数：{len(questions)}",
        f"- 去重后可导入总题数：**{len(all_items)}**（跳过重复题干 {skipped_dup} 题、无效 {skipped_invalid} 题）",
        "",
        "| 文件 | 学科 | 题数 | 大小 |",
        "|---|---|---|---|",
    ]

    for _, (subj_name, slug) in SUBJECT_MAP.items():
        items = by_slug.get(slug, [])
        if not items:
            continue
        fpath = out_dir / f"{slug}.json"
        payload = {"name": f"全学科题库-{subj_name}", "version": 2, "items": items}
        fpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        size_kb = round(fpath.stat().st_size / 1024, 1)
        lines.append(f"| `{slug}.json` | {subj_name} | {len(items)} | {size_kb} KB |")

    all_path = out_dir / "all.json"
    all_path.write_text(json.dumps({"name": "全学科题库-全部", "version": 2, "items": all_items}, ensure_ascii=False) + "\n", encoding="utf-8")
    all_mb = round(all_path.stat().st_size / 1024 / 1024, 2)
    lines.append(f"| `all.json` | 全部学科 | {len(all_items)} | {all_mb} MB |")
    lines.append("")
    lines.append("可在家长管理面板「题库 → 导入」或通过 `/api/questions` 批量导入。")

    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"导出完成：共 {len(all_items)} 题（跳过重复 {skipped_dup}，无效 {skipped_invalid}）-> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
