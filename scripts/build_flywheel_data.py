"""第 4 步：数据生产。把不通过的回答变成标注任务和偏好数据模板，交给标注同学改写。

用法：python scripts/build_flywheel_data.py --labels data/demo_labels.json
输出：
  flywheel/标注任务.csv          每条 FAIL 一行：问题、原回答、必须要点、禁止内容、归因，待填「改写后的回答」
  flywheel/偏好数据模板.jsonl     {prompt, rejected, chosen(待填), rubric}，改写完成后可用于 SFT 或偏好训练
  flywheel/验收抽样.csv           按 20% 抽样（每类至少 1 条），给第二位标注者复核
"""
import argparse
import csv
import json
import random
from collections import defaultdict

from common import CAUSES, ERROR_TAGS, ROOT, cases_by_id, write_jsonl


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    args = ap.parse_args()
    with open(args.labels, encoding="utf-8") as f:
        labels = json.load(f)["labels"]
    cases = cases_by_id()
    fails = [l for l in labels if l["verdict"] == "FAIL"]

    out = ROOT / "flywheel"
    out.mkdir(exist_ok=True)
    tasks, pairs = [], []
    for i, l in enumerate(fails, 1):
        c = cases[l["case_id"]]
        prompt = "\n".join(t["content"] for t in c["turns"])
        missed = [m for m, h in zip(c["must"], l["must_hit"]) if not h]
        broke = [m for m, h in zip(c["must_not"], l["must_not_hit"]) if h]
        tasks.append({
            "任务编号": f"T{i:03d}", "用例": l["case_id"], "版本": l["system"], "用户问题": prompt,
            "原回答": l.get("answer", ""), "漏掉的要点": "；".join(missed), "出现的禁止内容": "；".join(broke),
            "错误现象": "、".join(ERROR_TAGS.get(t, t) for t in l.get("tags", [])),
            "归因": CAUSES.get(l.get("cause"), ("", ""))[0], "标准级别": c["level"],
            "改写后的回答": "", "标注人": "", "复核人": "", "复核结论": "",
        })
        pairs.append({"id": f"T{i:03d}", "prompt": prompt, "rejected": l.get("answer", ""), "chosen": "",
                      "rubric": {"level": c["level"], "must": c["must"], "must_not": c["must_not"]}})

    with open(out / "标注任务.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(tasks[0]) if tasks else ["任务编号"])
        w.writeheader()
        w.writerows(tasks)
    write_jsonl(out / "偏好数据模板.jsonl", pairs)

    # 验收抽样：按归因分层，每层抽 20%，至少 1 条
    rng = random.Random(1)
    groups = defaultdict(list)
    for t in tasks:
        groups[t["归因"]].append(t)
    sample = []
    for g in groups.values():
        sample += rng.sample(g, max(1, round(len(g) * 0.2)))
    with open(out / "验收抽样.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["任务编号", "用例", "归因", "复核结论", "问题说明"])
        w.writeheader()
        w.writerows({"任务编号": t["任务编号"], "用例": t["用例"], "归因": t["归因"], "复核结论": "", "问题说明": ""} for t in sample)
    print(f"FAIL {len(fails)} 条 → 标注任务 {len(tasks)} 条，验收抽样 {len(sample)} 条，已写入 flywheel/")


if __name__ == "__main__":
    main()
