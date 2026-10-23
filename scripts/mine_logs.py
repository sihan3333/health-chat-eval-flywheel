"""第 0 步：从对话日志挖 Bad Case。把 CSV 装进 SQLite，执行 sql/log_mining.sql。

用法：python scripts/mine_logs.py [--csv data/sample_logs.csv]
输出：reports/日志挖掘.md、data/bad_case_candidates.csv（下一步人工复核，确认后补进评测集）
"""
import argparse
import csv
import sqlite3
from pathlib import Path

from common import DATA, REPORTS, ROOT

INT_COLS = {"day", "answer_len", "thumb", "regenerated", "neg_followup", "copied", "abandoned"}


def load(conn, path):
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0])
    conn.execute(f"CREATE TABLE chat_logs ({', '.join(cols)})")
    conn.executemany(
        f"INSERT INTO chat_logs VALUES ({', '.join('?' * len(cols))})",
        [[int(r[c]) if c in INT_COLS else r[c] for c in cols] for r in rows],
    )
    return len(rows)


def split_sql(text):
    """按「-- @名称」切分成 (名称, SQL) 列表。"""
    blocks, name, buf = [], None, []
    for line in text.splitlines():
        if line.startswith("-- @"):
            if name:
                blocks.append((name, "\n".join(buf)))
            name, buf = line[4:].strip(), []
        elif name:
            buf.append(line)
    if name:
        blocks.append((name, "\n".join(buf)))
    return blocks


def to_md(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(v) for v in r) + " |" for r in rows]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=str(DATA / "sample_logs.csv"))
    args = ap.parse_args()

    conn = sqlite3.connect(":memory:")
    n = load(conn, args.csv)
    md = ["# 日志挖掘结果", "", f"> 数据：`{Path(args.csv).name}`，共 {n} 条。**示例用的是模拟日志**，换成真实日志后重跑即可。", ""]
    candidates = None
    for name, sql in split_sql((ROOT / "sql" / "log_mining.sql").read_text(encoding="utf-8")):
        cur = conn.execute(sql)
        headers = [d[0] for d in cur.description]
        rows = cur.fetchall()
        md += [f"## {name}", "", to_md(headers, rows), ""]
        print(f"\n== {name}")
        for r in rows:
            print("  ", r)
        if name.startswith("Bad Case"):
            candidates = (headers, rows)

    md += ["## 下一步", "",
           "1. 人工复核候选问题：确认是回答质量问题，还是用户误操作、意图识别错误。",
           "2. 确认是质量问题的，改写成评测用例（补上标准级别、必须要点、禁止内容），加入评测集。",
           "3. 同一类问题出现 3 次以上，在归因看板里单独建一个错误类型持续跟踪。"]
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / "日志挖掘.md").write_text("\n".join(md), encoding="utf-8")
    if candidates:
        with open(DATA / "bad_case_candidates.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(list(candidates[0]) + ["复核结论", "对应评测用例"])
            w.writerows(list(r) + ["", ""] for r in candidates[1])
    print("\n已写入 reports/日志挖掘.md 和 data/bad_case_candidates.csv")


if __name__ == "__main__":
    main()
