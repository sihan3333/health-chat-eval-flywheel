"""第 1 步：让被测模型逐题作答。多轮题按真实多轮发送（先发第一句，拿到回复后再发第二句）。

用法：
  python scripts/generate.py --prompt v1 --tag 基线v1
  python scripts/generate.py --prompt v2 --tag 优化v2
  python scripts/generate.py --prompt v1 --tag 基线v1 --mock   # 不调接口，生成假回答跑通流程

没有公开 API 的 App：在 App 里手动提问，把回答粘贴到评测工作台（index.html）的标注台。
"""
import argparse
import random

from common import ROOT, RUNS, chat, load_eval_set, write_jsonl


def mock_answer(case, prompt_name, rng):
    """假回答：随机覆盖一部分要点，偶尔混入禁止内容。只用来验证流程，不代表任何模型。"""
    keep = 0.85 if prompt_name == "v2" else 0.6
    parts = [m for m in case["must"] if rng.random() < keep]
    if rng.random() < (0.08 if prompt_name == "v2" else 0.25):
        parts.append(case["must_not"][0])
    return "。".join(parts) or "建议多休息，注意观察。"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", default="v1", help="prompts/system_<prompt>.md")
    ap.add_argument("--tag", required=True, help="这一版的名字，会写进结果文件")
    ap.add_argument("--mock", action="store_true")
    args = ap.parse_args()

    system = (ROOT / "prompts" / f"system_{args.prompt}.md").read_text(encoding="utf-8")
    rng = random.Random(args.tag)
    rows = []
    for case in load_eval_set()["cases"]:
        if args.mock:
            answer, transcript = mock_answer(case, args.prompt, rng), []
        else:
            messages = [{"role": "system", "content": system}]
            transcript = []
            for turn in case["turns"]:
                messages.append(turn)
                reply = chat(messages)
                messages.append({"role": "assistant", "content": reply})
                transcript.append({"user": turn["content"], "assistant": reply})
            answer = transcript[-1]["assistant"]
        rows.append({"case_id": case["id"], "system": args.tag, "answer": answer, "transcript": transcript})
        print(f"{case['id']} 完成")

    out = RUNS / f"answers_{args.tag}.jsonl"
    write_jsonl(out, rows)
    print(f"已写入 {out}")


if __name__ == "__main__":
    main()
