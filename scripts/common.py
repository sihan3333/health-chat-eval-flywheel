"""公共工具：读评测集、调用 OpenAI 兼容接口、读写 jsonl。只用标准库。"""
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RUNS = ROOT / "runs"
REPORTS = ROOT / "reports"

# Windows 控制台默认不是 UTF-8，统一改掉，避免打印中文报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LEVELS = ["L0", "L1", "L2", "L3", "L4"]

# 错误现象标签（看到了什么）
ERROR_TAGS = {
    "T1": "大病小看（低估紧急程度）",
    "T2": "小病大看（过度警示）",
    "T3": "事实错误或幻觉",
    "T4": "用药建议不当",
    "T5": "漏掉关键要点",
    "T6": "没用上文信息或该追问没追问",
    "T7": "越权诊断或开药",
    "T8": "缺少共情或语气不当",
    "T9": "冗长或结构混乱",
}

# 归因（为什么错，交给谁修）
CAUSES = {
    "R1": ("模型知识缺失", "算法：补充 SFT 知识数据"),
    "R2": ("推理或上下文理解", "算法：补充多轮对话数据"),
    "R3": ("安全策略缺失", "策略：安全规则与系统提示词"),
    "R4": ("联网检索引入错误", "搜索：检索源与引用质量"),
    "R5": ("产品呈现与交互", "产品：卡片、追问组件、免责声明位置"),
    "R6": ("评测题本身有问题", "评测：修题或删题"),
}


def load_eval_set():
    with open(DATA / "eval_set.json", encoding="utf-8") as f:
        return json.load(f)


def cases_by_id():
    return {c["id"]: c for c in load_eval_set()["cases"]}


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def chat(messages, model=None, temperature=0.3):
    """调用任意 OpenAI 兼容接口（DeepSeek、混元、通义等）。

    环境变量：LLM_BASE_URL（如 https://api.deepseek.com/v1）、LLM_API_KEY、LLM_MODEL
    """
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    model = model or os.environ.get("LLM_MODEL", "")
    if not (base and key and model):
        sys.exit("缺少 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL，或者加 --mock 先跑通流程")
    body = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        base + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)["choices"][0]["message"]["content"]
