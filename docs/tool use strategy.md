#### `get_lead_context(lead_id)`

**调用时机：**

- 每次新会话开始时优先调用。
- 当需要判断客户已有信息时调用。
- 当用户没有重复提供背景，但系统可能已有历史信息时调用。

**目的：**

- 避免重复询问。
- 根据已有线索信息判断 qualification。
- 写 CRM 时补全上下文。

---

#### `search_knowledge_base(query)`

**调用时机：**

- 用户询问产品能力。
- 用户询问价格。
- 用户询问客户案例。
- 用户询问集成能力。
- 用户询问实施周期。
- 用户询问安全、权限、数据处理等基础信息。

**策略：**

如果知识库有明确答案，可以基于知识库回答。  
如果知识库没有明确答案，不能编造，应该说：

> 这个问题需要销售或方案同事进一步确认，我可以帮你转给人工同事。

---

#### `check_calendar(timezone, duration_minutes)`

**调用前置条件：**

必须已经确认：

- 邮箱
- 时区
- Demo 目的

**禁止行为：**

- 不能在没有时区时默认使用 `Asia/Shanghai`。
- 不能在用户没有明确 Demo 意图时直接查日历。
- 查到 slot 后不能直接说已预约。

---

#### `book_demo(lead_id, slot_id, attendee_email, summary)`

**调用前置条件：**

必须满足：

- 已经调用 `check_calendar`
- 用户明确选择某个 slot
- 已经有 attendee_email
- 已经有 demo summary / purpose

**调用成功后：**

才可以说：

> Demo 已预约成功。

然后调用 `write_crm_note`。

---

#### `write_crm_note(lead_id, summary, qualification_level, next_action)`

**调用时机：**

- 收集到有意义的新信息。
- 完成 Demo 预约。
- 转人工前后。
- 明确判断线索等级后。

**CRM summary 必须包含：**

- 客户痛点
- 当前阶段
- 下一步动作
- 信心等级

**注意：**

如果 Demo 只是 pending，不可写成 booked。

---

#### `handoff_to_human(lead_id, reason, urgency)`

**必须转人工或人工确认的场景：**

- 合同条款
- 法务问题
- 安全审计
- 定制报价
- SLA
- 私有化部署承诺
- 复杂集成承诺
- 客户要求保证转化率、ROI、成交结果
- 客户表达强烈购买意向但涉及商务谈判

---

### 防编造机制

新版 Agent 需要遵守一个简单原则：

> Anything not in tools, KB, or user-provided context is unknown.

具体机制：

1. **价格不编造**：价格只能来自知识库；没有则转人工。
2. **功能不夸大**：不能说“完全替代销售”“自动成交”“保证提升”。
3. **案例不编造**：没有知识库案例就不能说“我们服务过某某客户”。
4. **预约不幻想**：只有 `book_demo` 成功才是 booked。
5. **CRM 不提前写结果**：状态必须和工具结果一致。
6. **高风险问题自动打 risk flag**：如 `pricing_request`、`security_audit`、`legal_contract`、`custom_quote`。