# AI 健康问答：评测体系与数据飞轮

为 AI 对话助手的健康问答场景搭一套「问题发现 → 评测分析 → 数据生产 → 模型优化 → 效果验证」闭环。

**在线演示**：https://sihan3333.github.io/health-chat-eval-flywheel/

**先看**：[项目方案.md](项目方案.md)（完整思路）→ 在线评测工作台

## 文件

| 路径 | 内容 |
|---|---|
| `index.html` + `web/` | 评测工作台：项目总览、评测标准、评测集、标注台、GSB 对比、看板、数据飞轮 |
| `data/eval_set.json` | 36 题评测集（自拟，待医学复核） |
| `data/sample_logs.csv` | 1200 条**模拟**对话日志 |
| `data/demo_labels.json` | **示例**标注数据（随机生成，只演示看板） |
| `sql/log_mining.sql` | 日志挖掘 SQL |
| `prompts/` | 被测系统提示词 v1 / v2、评审员提示词 |
| `scripts/` | 全流程脚本（只用 Python 标准库） |
| `reports/` | 评测报告、日志挖掘结果（当前是示例数据跑的） |
| `flywheel/` | 标注任务、偏好数据模板、验收抽样表 |

## 怎么运行

打开工作台（直接双击 `index.html` 也能用）：

```bash
python -m http.server 8765
```

然后访问 http://localhost:8765 。

全流程（没有 API Key 时加 `--mock` 跑通流程）：

```bash
python scripts/make_sample_logs.py
python scripts/mine_logs.py
python scripts/make_demo_labels.py
python scripts/generate.py --prompt v1 --tag 基线v1 --mock
python scripts/judge.py --tag 基线v1 --mock
python scripts/analyze.py --labels data/demo_labels.json
python scripts/build_flywheel_data.py --labels data/demo_labels.json
```

用真实模型跑（任意 OpenAI 兼容接口，例如 DeepSeek）：先设置环境变量 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`，可选 `JUDGE_MODEL`，再去掉 `--mock`。

## 接下来要做（让项目有真实结果）

1. **产品实测**：挑两款主流中文对话助手，按原话问 36 题（多轮题分两句发，每题新开对话），把回答粘贴到标注台。导出 `labels.json` 放进 `data/`。
2. **策略优化验证**：用 DeepSeek API 跑 `--prompt v1` 和 `--prompt v2`，把回答导入标注台人工标注，再跑 `judge.py` 和 `analyze.py --judge ...` 校准评审员。
3. 用真实结果替换示例数据。
4. 推到 GitHub 开 Pages，和其他作品一样放链接。

## 数据说明

评测集依据公开指南自拟、待医学复核；日志和示例标注均为模拟数据。本项目不构成医疗建议。
