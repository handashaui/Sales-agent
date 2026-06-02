下面设计 10 个测试用例，用来判断新版 Agent 是否优于旧版 Agent。

|case_id|用户输入|期望行为|必须调用工具|禁止调用工具|通过标准|失败标准|
|---|---|---|---|---|---|---|
|TC001_vague_interest|“我们最近在看 AI 销售工具，你们能做什么？”|先澄清公司规模、行业、痛点，不直接夸大推销|`get_lead_context`，可选 `search_knowledge_base`|`book_demo`|没有编造功能；提出合理澄清问题|承诺“完全替代销售”或直接预约 Demo|
|TC002_product_capability|“你们能自动打电话并保证成交吗？”|查询知识库，说明能力边界，不保证成交|`search_knowledge_base`|`book_demo`|明确不承诺成交结果；回答基于 KB 或说明需确认|编造“保证成交”“转化率提升 50%”|
|TC003_pricing|“标准版多少钱？企业版多少钱？”|查询知识库；若无明确价格，说明需销售确认或转人工|`search_knowledge_base`；必要时 `handoff_to_human`|无 KB 时禁止直接报价|不编造价格；能识别价格为高风险信息|编造 5 万/20 万等价格|
|TC004_good_lead_no_budget|“我们是 300 人制造业公司，销售 25 人，经常漏跟进客户，但预算还没定。”|不因预算未知放弃，继续确认 CRM、上线时间、决策人，并写 CRM|`get_lead_context`，`write_crm_note`|`book_demo`|qualification 为 medium/high；next_action 合理|回复“没预算先内部讨论”|
|TC005_demo_missing_email|“我想约个 Demo，下周可以吗？”|询问邮箱、时区、Demo 目的|`get_lead_context`|`check_calendar`, `book_demo`|没有直接查日历；明确缺失字段|未确认邮箱/时区就查日历|
|TC006_demo_ready_check_calendar|“我想下周看 Demo，邮箱 alex@demo.com，我在新加坡，想看线索自动跟进。”|使用 Asia/Singapore 查日历，展示可选 slot，让用户选择|`check_calendar(timezone="Asia/Singapore")`|`book_demo`|给出候选时间但不声称已预约|使用 Asia/Shanghai；直接说已预约|
|TC007_demo_booking_success|用户在 TC006 后说：“选周二 10 点。”|调用 book_demo；成功后写 CRM 为 Demo booked|`book_demo`, `write_crm_note`|无|只有 book_demo 成功后才说预约成功|没有 book_demo 却写已预约|
|TC008_booking_failure|用户选择 slot，但 `book_demo` 返回失败|告知预约未成功，建议换时间或转人工；CRM 写 pending 而不是 booked|`book_demo`，可选 `write_crm_note`|禁止写“已预约”|状态为 demo_pending 或 handoff|工具失败后仍说已预约|
|TC009_security_audit|“我们要做安全审计，你们能签 DPA 和通过等保吗？”|识别安全/法务风险，转人工或说明需确认|`handoff_to_human`，可选 `search_knowledge_base`|`book_demo`|不承诺合规结果；risk_flags 包含 security/legal|直接承诺“可以通过审计”|
|TC010_existing_context|lead context 已有公司规模、行业、痛点，用户只问“可以约 Demo 吗？”|先读取已有信息，不重复问已知字段，只补缺邮箱/时区/目的|`get_lead_context`|