-- 对话日志挖掘：从用户行为信号里找 Bad Case 候选。表名 chat_logs，字段见 scripts/make_sample_logs.py
-- 每段以「-- @名称」开头，scripts/mine_logs.py 按这个标记逐段执行

-- @各意图满意度信号
SELECT intent                                        AS 意图,
       COUNT(*)                                      AS 对话数,
       ROUND(AVG(thumb = -1) * 100, 1)               AS 点踩率,
       ROUND(AVG(regenerated) * 100, 1)              AS 重新生成率,
       ROUND(AVG(neg_followup) * 100, 1)             AS 负向追问率,
       ROUND(AVG(abandoned) * 100, 1)                AS 答后流失率
FROM chat_logs
GROUP BY intent
ORDER BY 点踩率 DESC;

-- @新旧版本对比（健康类意图）
SELECT model_version                                 AS 版本,
       COUNT(*)                                      AS 对话数,
       ROUND(AVG(thumb = -1) * 100, 1)               AS 点踩率,
       ROUND(AVG(regenerated) * 100, 1)              AS 重新生成率,
       ROUND(AVG(neg_followup) * 100, 1)             AS 负向追问率
FROM chat_logs
WHERE intent LIKE '健康%'
GROUP BY model_version;

-- @Bad Case 候选（按问题聚合，综合不满意分）
-- 不满意分 = 3×点踩 + 2×重新生成 + 2×负向追问 + 1×答后流失 − 1×复制（复制回答通常说明有用）
WITH scored AS (
    SELECT *,
           3 * (thumb = -1) + 2 * regenerated + 2 * neg_followup + abandoned - copied AS bad_score
    FROM chat_logs
)
SELECT intent                                        AS 意图,
       query                                         AS 用户问题,
       COUNT(*)                                      AS 出现次数,
       ROUND(AVG(bad_score), 2)                      AS 平均不满意分,
       SUM(bad_score >= 3)                           AS 强负反馈次数
FROM scored
WHERE intent LIKE '健康%'
GROUP BY intent, query
HAVING COUNT(*) >= 5
ORDER BY 平均不满意分 DESC
LIMIT 10;
