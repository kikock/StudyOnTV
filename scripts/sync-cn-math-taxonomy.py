#!/usr/bin/env python3
"""从 cn-math-taxonomy 仓库生成 StudyOnTV v2 格式的可导入题库文件（仅保留单选与判断题，填空题自动转为单选/判断，移除主观题）。"""

import base64
import collections
import hashlib
import json
import re
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


def deterministic_shuffle(items: list[str], seed_str: str) -> list[str]:
    """按题目 ID 确定性打乱选项顺序，保证可复现且正确选项下标均匀分布。"""
    return sorted(items, key=lambda x: hashlib.md5(f"{seed_str}:{x}".encode("utf-8")).hexdigest())


def numeric_distractors(ans: str, qid: str) -> list[str]:
    """为数值/坐标/分数类填空答案生成 3 个不重复的合理干扰项。"""
    s = ans.strip()
    cands: list[str] = []

    # 1) 纯整数
    if re.fullmatch(r"-?\d+", s):
        n = int(s)
        offsets = [1, -1, 2, -2, 10, -10, 3, -3, 4, 5]
        for off in offsets:
            v = n + off
            if n >= 0 and v < 0:
                continue
            cand = str(v)
            if cand != s and cand not in cands:
                cands.append(cand)
            if len(cands) >= 3:
                return cands[:3]

    # 2) 纯小数
    m_dec = re.fullmatch(r"(-?\d+)\.(\d+)", s)
    if m_dec:
        prec = len(m_dec.group(2))
        val = float(s)
        step = 10 ** (-prec)
        for mult in (1, -1, 2, -2, 10, -10, 5, -5):
            v = round(val + mult * step, prec)
            if val >= 0 and v < 0:
                continue
            cand = f"{v:.{prec}f}"
            if cand != s and cand not in cands:
                cands.append(cand)
            if len(cands) >= 3:
                return cands[:3]

    # 3) 分数 a/b
    m_frac = re.fullmatch(r"(-?\d+)/(\d+)", s)
    if m_frac:
        num, den = int(m_frac.group(1)), int(m_frac.group(2))
        for dn, dd in ((1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (1, 1)):
            nn, nd = num + dn, den + dd
            if nd <= 1:
                continue
            if num >= 0 and nn < 0:
                continue
            cand = f"{nn}/{nd}"
            if cand != s and cand not in cands:
                cands.append(cand)
            if len(cands) >= 3:
                return cands[:3]

    # 4) 多值/逗号分隔（如 "2，3"）
    sep = "，" if "，" in s else ("," if "," in s else None)
    if sep:
        parts = [p.strip() for p in s.split(sep)]
        if len(parts) >= 2 and re.fullmatch(r"-?\d+", parts[0]):
            n0 = int(parts[0])
            for off in (1, -1, 2, -2):
                v0 = n0 + off
                if n0 >= 0 and v0 < 0:
                    continue
                cand = sep.join([str(v0)] + parts[1:])
                if cand != s and cand not in cands:
                    cands.append(cand)
                if len(cands) >= 3:
                    return cands[:3]

    return cands[:3]


def algebraic_distractors(ans: str, pool: list[str], qid: str) -> list[str]:
    """为代数式/短文本答案生成 3 个不重复干扰项，不足时从同科短答案池补充。"""
    s = ans.strip()
    cands: list[str] = []

    # 尝试简单符号/数字扰动
    swaps = [
        ("+", "-"), ("-", "+"), ("=", "≠"),
        ("2", "3"), ("3", "2"), ("1", "2"), ("5", "4"),
    ]
    for old, new in swaps:
        if old in s:
            cand = s.replace(old, new, 1)
            if cand != s and cand not in cands:
                cands.append(cand)
            if len(cands) >= 3:
                return cands[:3]

    # 从同科短答案池确定性挑选不同答案补足 3 个
    ordered_pool = deterministic_shuffle([p for p in pool if p and p != s], qid)
    for p in ordered_pool:
        if p not in cands:
            cands.append(p)
        if len(cands) >= 3:
            break

    while len(cands) < 3:
        cands.append(f"以上都不对（{len(cands) + 1}）")
    return cands[:3]


def convert_question(q: dict, topics: dict, short_pools: dict[str, list[str]]) -> tuple[str, dict | None]:
    """将单道 cn-math-taxonomy 题目转换为 StudyOnTV v2 格式（仅 single / boolean）。"""
    qid = q["id"]
    prefix = qid.split("_")[0]
    subj_name, slug = SUBJECT_MAP.get(prefix, ("常识", "general"))
    topic = topics.get(q.get("topicId", ""), {})
    level = GRADE_MAP.get(topic.get("grade"), "")
    prompt = (q.get("prompt") or "").strip()
    if not prompt or len(prompt) > 5000:
        return slug, None

    qtype = q.get("type")
    # 去掉主观题
    if qtype == "self":
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
        return slug, item

    if qtype in ("numeric", "short"):
        ans = str(q.get("answer") or "").strip()
        if not ans:
            return slug, None
        # 是/否类直接转为判断题
        if ans in ("是", "对", "正确"):
            item["type"] = "boolean"
            item["k"] = 0
            return slug, item
        if ans in ("不是", "错", "错误", "否"):
            item["type"] = "boolean"
            item["k"] = 1
            return slug, item

        distractors = numeric_distractors(ans, qid)
        if len(distractors) < 3:
            extra = algebraic_distractors(ans, short_pools.get(prefix, []), qid)
            for e in extra:
                if e != ans and e not in distractors:
                    distractors.append(e)
                if len(distractors) >= 3:
                    break
        opts = deterministic_shuffle([ans] + distractors[:3], qid)
        item["type"] = "single"
        item["a"] = opts
        item["k"] = opts.index(ans)
        return slug, item

    return slug, None


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

    # 预收集各学科短文本/非数值答案池，用于生成同类干扰项
    short_pools: dict[str, list[str]] = collections.defaultdict(list)
    for q in questions:
        if q.get("type") in ("short", "numeric"):
            ans = str(q.get("answer") or "").strip()
            if ans and ans not in ("是", "不是", "对", "错", "正确", "错误", "否"):
                short_pools[q["id"].split("_")[0]].append(ans)

    out_dir = repo_root / "data" / "banks" / "cn-math-taxonomy"
    out_dir.mkdir(parents=True, exist_ok=True)

    by_slug: dict[str, list[dict]] = collections.defaultdict(list)
    all_items: list[dict] = []
    seen_stems: set[str] = set()
    type_counts: collections.Counter = collections.Counter()
    skipped_dup = 0
    skipped_removed = 0

    for q in questions:
        slug, item = convert_question(q, topics, short_pools)
        if item is None:
            skipped_removed += 1
            continue
        stem_key = item["q"]
        if stem_key in seen_stems:
            skipped_dup += 1
            continue
        seen_stems.add(stem_key)
        by_slug[slug].append(item)
        all_items.append(item)
        type_counts[item["type"]] += 1

    lines = [
        "# cn-math-taxonomy 可导入题库（StudyOnTV v2 格式）",
        "",
        f"- 源题库总题数：{len(questions)}",
        f"- 去重后可导入总题数：**{len(all_items)}**（单选 {type_counts['single']} 题、判断 {type_counts['boolean']} 题；已移除主观题并跳过重复题干共 {skipped_dup + skipped_removed} 题）",
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
    print(f"导出完成：共 {len(all_items)} 题（single={type_counts['single']}, boolean={type_counts['boolean']}, 跳过重复 {skipped_dup}, 移除/跳过 {skipped_removed}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
