"""生成【示例】标注数据，并把评测集和示例数据打包成网页能直接读的 JS 文件。

示例数据是随机生成的，只用来演示看板和分析脚本，不是任何模型的真实评测结果。
真实结果请在评测工作台里标注后导出，替换 data/labels.json。

输出：data/demo_labels.json、web/data.js
"""
import json
import random

from common import DATA, LEVELS, ROOT, load_eval_set

SYSTEMS = ["基线v1", "优化v2"]
# 两个版本在各类题上的「答好」概率（模拟设定）
SKILL = {"基线v1": {"A": .7, "B": .6, "C": .7, "D": .6, "E": .45, "F": .4},
         "优化v2": {"A": .9, "B": .85, "C": .8, "D": .85, "E": .85, "F": .75}}


def simulate(case, system, rng):
    good = rng.random() < SKILL[system][case["category"]]
    must_hit = [1 if good or rng.random() < 0.55 else 0 for _ in case["must"]]
    must_not_hit = [0 if good or rng.random() < 0.6 else 1 for _ in case["must_not"]]
    std = LEVELS.index(case["level"])
    if good:
        level = rng.choice(case["acceptable"])
    else:
        # 答得不好时，高风险题更容易被低估，低风险题更容易被夸大
        shift = -rng.choice([1, 2]) if std >= 3 else rng.choice([-1, 0, 1, 2])
        level = LEVELS[max(0, min(4, std + shift))]
    if good and not all(must_hit):
        must_hit = [1] * len(must_hit)

    tags, cause = [], ""
    if LEVELS.index(level) < min(LEVELS.index(a) for a in case["acceptable"]):
        tags.append("T1")
    if LEVELS.index(level) > max(LEVELS.index(a) for a in case["acceptable"]):
        tags.append("T2")
    if any(must_not_hit):
        tags.append({"B": "T4", "E": "T7", "C": "T3"}.get(case["category"], "T3"))
    if not all(must_hit):
        tags.append("T6" if case["category"] == "F" else "T5")
    if tags:
        first = tags[0]
        cause = {"T1": "R3", "T2": "R3", "T7": "R3", "T6": "R2", "T3": "R1", "T4": "R1"}.get(first, rng.choice(["R1", "R3", "R4", "R5"]))
        if rng.random() < 0.15:
            tags.append(rng.choice(["T8", "T9"]))
    verdict = "PASS" if all(must_hit) and not any(must_not_hit) and level in case["acceptable"] else "FAIL"
    return {"case_id": case["id"], "system": system, "answer": "（示例数据，无回答原文）",
            "level_given": level, "must_hit": must_hit, "must_not_hit": must_not_hit,
            "verdict": verdict, "tags": tags, "cause": cause, "note": ""}


def main():
    rng = random.Random(7)
    ev = load_eval_set()
    labels = [simulate(c, s, rng) for c in ev["cases"] for s in SYSTEMS]

    # 模拟评审员：大体跟人工一致，偶尔把「漏要点」放过去（这就是要校准的地方）
    judge = []
    for lb in labels:
        content_ok = all(lb["must_hit"]) and not any(lb["must_not_hit"])
        flip = rng.random() < (0.18 if not content_ok else 0.07)
        judge.append({"case_id": lb["case_id"], "system": lb["system"],
                      "verdict": ("PASS" if content_ok else "FAIL") if not flip else ("FAIL" if content_ok else "PASS")})

    by = {(l["case_id"], l["system"]): l for l in labels}
    gsb = []
    for c in ev["cases"]:
        a, b = by[(c["id"], "基线v1")], by[(c["id"], "优化v2")]
        score = lambda x: (x["verdict"] == "PASS") * 2 + sum(x["must_hit"]) / len(x["must_hit"]) - sum(x["must_not_hit"])
        d = score(b) - score(a)
        gsb.append({"case_id": c["id"], "a": "基线v1", "b": "优化v2",
                    "result": "G" if d > 0.2 else ("B" if d < -0.2 else "S")})

    demo = {"meta": {"note": "示例数据：随机生成，只用于演示看板，不是任何模型的真实结果", "systems": SYSTEMS},
            "labels": labels, "gsb": gsb, "judge": judge}
    (DATA / "demo_labels.json").write_text(json.dumps(demo, ensure_ascii=False, indent=1), encoding="utf-8")

    web = ROOT / "web"
    web.mkdir(exist_ok=True)
    (web / "data.js").write_text(
        "// 自动生成：python scripts/make_demo_labels.py\n"
        f"window.EVAL_SET = {json.dumps(ev, ensure_ascii=False)};\n"
        f"window.DEMO_LABELS = {json.dumps(demo, ensure_ascii=False)};\n",
        encoding="utf-8")
    print(f"示例标注 {len(labels)} 条 → data/demo_labels.json；网页数据 → web/data.js")


if __name__ == "__main__":
    main()
