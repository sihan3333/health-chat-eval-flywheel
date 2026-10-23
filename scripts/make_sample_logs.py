"""生成【模拟】对话日志，用来演示日志挖掘流程。数据全部是随机生成的，不是任何真实产品的日志。

字段：session_id, day, model_version, intent, query, answer_len,
      thumb(1 赞 / -1 踩 / 0 无), regenerated, neg_followup(追问「不对」「你说错了」), copied, abandoned
"""
import csv
import random

from common import DATA

QUERIES = {
    "健康-症状": ["发烧 38 度要不要去医院", "胸口闷是怎么回事", "嗓子疼吃什么药", "头疼了三天", "肚子右下方疼",
                "宝宝发烧 38 度 2 个月大", "晚上总是咳嗽", "拉肚子一天了"],
    "健康-用药": ["布洛芬和对乙酰氨基酚能一起吃吗", "吃头孢能喝酒吗", "阿莫西林一次吃几粒", "孕妇感冒能吃什么药",
                "降压药漏吃了怎么办", "华法林能和阿司匹林一起吃吗", "被狗抓了没出血要打疫苗吗", "他汀能喝西柚汁吗"],
    "健康-报告": ["尿酸高要吃药吗", "甲状腺结节 3 类严重吗", "转氨酶高是肝炎吗", "幽门螺杆菌阳性怎么办", "血常规白细胞高"],
    "健康-照护": ["老人记不清吃没吃药", "我妈老忘事是痴呆吗", "老人摔倒了站不起来", "爸爸血压 170 头晕", "怎么劝爸妈体检"],
    "健康-心理": ["最近很焦虑睡不着", "感觉活着没意思", "压力大怎么办"],
    "其他": ["帮我写周报", "推荐一本书", "翻译这段话", "北京明天天气"],
}
# 各意图的基础不满意倾向（模拟设定，用于让挖掘结果有差异）
BASE_BAD = {"健康-症状": 0.10, "健康-用药": 0.16, "健康-报告": 0.09, "健康-照护": 0.12, "健康-心理": 0.18, "其他": 0.05}
# 模拟「明显答得不好」的几类问题，挖掘时应该能被找出来
HOT_BAD = {"被狗抓了没出血要打疫苗吗": 0.45, "阿莫西林一次吃几粒": 0.35, "老人记不清吃没吃药": 0.38,
           "感觉活着没意思": 0.40, "宝宝发烧 38 度 2 个月大": 0.42}
WEIGHTS = {"健康-症状": 20, "健康-用药": 18, "健康-报告": 10, "健康-照护": 8, "健康-心理": 5, "其他": 39}


def main():
    rng = random.Random(20261022)
    rows = []
    intents = list(WEIGHTS)
    for i in range(1200):
        intent = rng.choices(intents, weights=[WEIGHTS[k] for k in intents])[0]
        query = rng.choice(QUERIES[intent])
        day = 1 + i * 14 // 1200
        version = "v1" if day <= 7 else "v2"  # 第 8 天起上线新版（模拟）
        p_bad = HOT_BAD.get(query, BASE_BAD[intent]) * (0.6 if version == "v2" and intent != "其他" else 1)
        bad = rng.random() < p_bad
        thumb = -1 if bad and rng.random() < 0.5 else (1 if not bad and rng.random() < 0.12 else 0)
        rows.append({
            "session_id": f"s{i:05d}", "day": day, "model_version": version, "intent": intent, "query": query,
            "answer_len": int(rng.gauss(420 if intent != "其他" else 260, 90)),
            "thumb": thumb,
            "regenerated": int(bad and rng.random() < 0.45),
            "neg_followup": int(bad and rng.random() < 0.35),
            "copied": int(not bad and rng.random() < 0.15),
            "abandoned": int(rng.random() < (0.3 if bad else 0.08)),
        })
    out = DATA / "sample_logs.csv"
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"已生成 {len(rows)} 条模拟日志 → {out}")


if __name__ == "__main__":
    main()
