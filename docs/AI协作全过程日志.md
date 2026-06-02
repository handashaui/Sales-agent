# AI 协作全过程日志

项目仓库：[handashaui/Sales-agent](https://github.com/handashaui/Sales-agent)

开发日期：2026-06-01

## 1. 使用的 AI 工具

### 使用了哪些工具/模型：

- ChatGPT / Codex：用于需求拆解、代码框架设计、测试用例设计、Debug 和文档整理。
- Langfuse：项目中预留为可选的观测与评分记录工具，用于记录每个 eval case 的 trace、固定规则分数和 LLM-as-judge 结果。
- Obsedian：用来写文字记录

### 每个工具分别用于什么：

- ChatGPT / Codex：帮助我把“销售 Agent”这个宽泛目标拆成 Agent 输入输出、工具调用、状态管理、评测集、文档几个部分，并在实现过程中检查逻辑漏洞。
- Langfuse：用于模拟线上 Agent 的可观测性，把每个测试 case 的输出和分数记录下来，便于之后追踪失败样例。
- Python / pytest：实现可运行的 CLI、service、Agent 主逻辑、mock tools 和 eval runner，并用测试保证关键流程不回归。

### 为什么选择这些工具：

- 这个项目需要的不只是聊天回复，而是一个可测试、可复现的销售 Agent Harness，所以选择 Python 作为主实现语言。
- 销售 Agent 很容易出现“编造价格、客户案例、ROI 承诺”等问题，因此需要固定规则评测和 LLM-as-judge 双重验证。
- Langfuse 适合记录 Agent 轨迹和评测分数，虽然本地运行时可选，但架构上提前留出接口。

## 2. 问题拆解

### 我最初如何理解问题：

我最初把任务理解为：实现一个面向 B2B 销售线索跟进的 Agent，不只是生成一句销售话术，而是要能识别用户意图、调用工具、维护状态、避免违规承诺，并且能通过自动化评测证明它的行为可靠。

### 我把问题拆成了哪些子任务：

1. 定义 Agent 的输入输出格式：输入包括 `lead_id` 和多轮对话，输出包括 `assistant_message`、`tool_calls`、`state`。
2. 设计销售场景状态：包括线索等级、缺失信息、下一步动作、风险标记、Demo 状态、CRM 是否更新、是否需要人工接管等。
3. 实现 mock tools：包括获取 lead context、知识库搜索、查日历、预约 Demo、写 CRM note、人工转接。
4. 实现确定性 Agent 策略：识别 Demo、价格问题、客户案例问题、合同/采购问题、低质量线索、多轮跟进等场景。
5. 编写 eval runner：对 JSON 稳定性、工具顺序、状态正确性、禁止编造、人工接管、Demo 流程等维度打分。
6. 构造测试集：覆盖 12 个销售 Agent 典型用例。
7. 补充文档和 Excel：写 README、评测说明、AI 迭代日志，并生成 Excel 测试集。

### 哪些部分交给 AI，哪些部分必须自己判断：

- 交给 AI 的部分：代码框架草拟、测试用例扩展、README 文档初稿、eval 维度建议、错误原因排查。
- 必须自己判断的部分：销售 Agent 的业务边界、哪些承诺不能说、什么时候需要人工接管、评测 case 是否真实覆盖核心风险、最终输出是否符合项目要求。

## 3. 关键 Prompt 记录

### Prompt 1

**Prompt：**

> 请帮我设计一个 Sales Agent Harness，要求能处理销售线索跟进、工具调用、状态输出和自动化评测，代码尽量小而完整。

**目的：**

明确项目整体架构，避免一开始只写成普通聊天机器人。

**AI 输出摘要：**

AI 建议把项目拆成 agent、tools、models、eval_runner、cli 几个模块，并使用稳定 JSON 输出记录工具轨迹和状态。

**我采纳了什么，没有采纳什么，原因：**

我采纳了模块化结构和稳定 JSON 输出；没有完全采纳复杂工作流编排框架，因为项目规模较小，用简单 Python 类更容易测试和展示。

### Prompt 2

**Prompt：**

> 销售 Agent 需要避免哪些高风险回复？请帮我列出评测维度和典型失败 case。

**目的：**

确定测试集的风险覆盖面。

**AI 输出摘要：**

AI 提到不能编造价格、客户案例、ROI 承诺，不能在用户要求合同或采购流程时继续自动答复，Demo 预约必须确认邮箱和时间。

**我采纳了什么，没有采纳什么，原因：**

我采纳了“禁止编造”和“人工接管”两个核心评测维度；没有采纳过于泛化的客服礼貌评分，因为这个项目更关注工具行为和安全边界。

### Prompt 3

**Prompt：**

> 请根据 B2B 销售线索跟进场景，生成 10 个以上 eval cases，覆盖 Demo、价格、客户案例、低质量 lead、多轮对话和 JSON 稳定性。

**目的：**

快速扩展测试集，避免只靠一个 demo case 验证。

**AI 输出摘要：**

AI 给出了制造业高意向线索、Demo 预约、缺少邮箱、价格问题、合同请求、客户案例、学生调研、时区、多轮状态等场景。

**我采纳了什么，没有采纳什么，原因：**

我采纳了 12 个 case 的方向，并手动调整了中文表达和 expected_state；没有直接照搬所有期望工具，因为部分工具顺序需要和实际 Agent 实现保持一致。

### Prompt 4

**Prompt：**

> 帮我检查当前 Agent 为什么 eval 中 CRM note 明明写入了，但 public tool_calls 里看不到。

**目的：**

定位一次工具轨迹记录不一致的问题。

**AI 输出摘要：**

AI 指出内部 `state.trajectory` 和对外返回的 `tool_calls` 使用了不同列表，某些路径调用 `write_crm_note` 时没有传入 public accumulator。

**我采纳了什么，没有采纳什么，原因：**

我采纳了“把 visible tool call accumulator 传入 CRM note 写入函数”的修复；没有把所有内部轨迹都直接暴露，因为对外输出仍应只展示必要工具调用。

### Prompt 5

**Prompt：**

> eval 里学生调研 lead 被识别成普通业务咨询，大公司无预算但有明确痛点只给 medium，怎么改更合理？

**目的：**

修正线索分级策略，让评分更符合销售业务逻辑。

**AI 输出摘要：**

AI 建议先识别“学生、作业、研究”这类低意向词，再对公司规模、销售团队、线索痛点、Demo 意图做加权评分；无预算不应直接降低高意向线索。

**我采纳了什么，没有采纳什么，原因：**

我采纳了低意向优先识别和高意向加权规则；没有采用“必须询问预算”的建议，因为销售 Agent 不应该 budget-first，尤其用户已经表达明确业务痛点时。

### Prompt 6

**Prompt：**

> 请帮我把 eval 结果和项目使用方式写进 README，并补充一个 AI iteration log。

**目的：**

让项目可以被别人复现运行，并记录 AI 协作过程。

**AI 输出摘要：**

AI 生成了安装命令、运行 Agent、运行 eval、生成 Excel、架构说明、已知问题和迭代记录。

**我采纳了什么，没有采纳什么，原因：**

我采纳了 README 的主体结构和 eval summary；没有保留过长的解释段落，因为项目提交更需要清晰命令和结果。

## 4. 迭代过程

### 版本 v1：Baseline Harness

**主要方案：**

先实现最小可运行版本：`SalesAgent.run()` 接收 `lead_id` 和 conversation，调用 `get_lead_context`，根据关键词判断是否预约 Demo、是否继续询问、是否写 CRM，并返回 JSON。

**发现的问题：**

- 初版只验证了 Demo case，覆盖面太窄。
- CLI smoke test 后生成的 Python bytecode 文件曾经被误加入版本管理。
- 工具调用轨迹和状态输出虽然能跑，但还不能证明 Agent 在价格、合同、客户案例等风险场景下安全。

### 版本 v2：Evaluation Coverage

**改动：**

加入 12 个 eval cases，覆盖制造业线索、Demo 预约、缺少邮箱、价格问题、合同人工接管、客户案例、学生调研、时区、JSON 稳定性和多轮状态更新。

**原因：**

销售 Agent 的风险不在“能不能回复”，而在“什么时候不该乱说”和“工具调用是否符合流程”。因此必须用测试集约束行为。

**效果：**

项目从单个 demo 变成可自动评测的 harness。评测输出包括 `eval_results.json` 和 `eval_summary.csv`，后续可以接入 Langfuse。

### 版本 v3：Policy And Qualification Fixes

**改动：**

- 对学生/作业/研究类 lead 优先判定为低意向。
- 对大公司、销售团队、明确线索痛点的 lead 提升为高意向，即使预算未确定也不应被拒绝。
- 修复 `write_crm_note` 在部分路径中没有出现在 public `tool_calls` 的问题。

**原因：**

初版策略过于依赖关键词，导致“学生调研”和“真实企业但没预算”两个场景判断不够符合业务逻辑。

**效果：**

固定规则评测达到 12/12，通过率 100%，平均分 1.0。

### 版本 v4：Real LLM And Observability Hooks

**改动：**

加入可选 OpenAI 消息润色和 Langfuse scoring wrapper，但保持工具路由和状态迁移为确定性逻辑。

**原因：**

如果让 LLM 直接决定工具调用，eval 容易不稳定；如果完全不用 LLM，回复又可能比较机械。所以最终把 LLM 放在“最后润色”位置。

**效果：**

项目既能本地无 API Key 稳定运行，也能在有 API Key 和 Langfuse 配置时演示更接近真实线上 Agent 的观测能力。

## 5. 评测或验证过程

### 我如何验证最终答案（测试 case）：

我主要用了两类验证：

1. 单元测试：

```bash
python -m pytest -q
```

实际结果：

```text
5 passed in 0.01s
```

2. 自动化 eval：

```bash
PYTHONPATH=src python -m sales_agent_harness.eval_runner \
  --cases evals/sales_cases.json \
  --output-dir eval_results
```

实际结果：

```text
case_count=12
pass_count=12
average_score=1.0
```

测试集覆盖的 case 包括：

- 制造业高意向线索不能因为没有预算就被放弃。
- 新加坡 Demo 预约需要查日历、预约、写 CRM。
- 没有邮箱时不能直接预约 Demo。
- 价格和 ROI 问题不能编造数字或承诺。
- 合同、采购、真人销售请求需要人工接管。
- 指名客户案例不能编造。
- 学生作业类需求应判定为低意向。
- 上海和新加坡时区要能进入正确 Demo 流程。
- 普通咨询也必须返回稳定 JSON。
- 多轮对话后要更新 CRM。

### 哪些 case 失败了，我如何修复：

- `case_007_low_quality_lead` 初期失败：学生作业场景被当成普通业务咨询。修复方式是在 qualification 前优先识别“学生/作业”等低意向信号。
- `case_009_no_budget_but_real_pain` 初期得分偏低：真实企业有明确痛点但预算未定，被判为 medium。修复方式是把公司规模、销售团队、线索痛点作为高意向信号，不把预算作为第一判断条件。
- CRM trace 相关 case 初期不完整：某些路径实际写了 CRM，但 public `tool_calls` 没展示。修复方式是统一把 visible tool call accumulator 传入 `write_crm_note`。

## 6. AI 输出错误记录

### 错误 1

**AI 建议：**

AI 一开始建议在销售资格判断中优先询问“预算是多少”。

**为什么不对：**

这不符合本项目策略。B2B 销售线索跟进不应该 budget-first，尤其当用户已经说明公司规模、销售团队和痛点时，直接追问预算会显得过早，也会导致高意向 lead 被错误降级。

**我是如何发现并修改的：**

我通过 `case_001_manufacturing_qualify` 和 `case_009_no_budget_but_real_pain` 发现这个问题。后来把判断逻辑改为先看业务痛点、公司规模、销售团队和 Demo 意图，预算不作为首要门槛。

### 错误 2

**AI 建议：**

AI 曾建议对价格、ROI、客户案例问题直接生成更像销售话术的回答，例如“我们可以做到 ROI 提升”或“有类似客户案例”。

**为什么不对：**

这些内容如果没有知识库依据就是编造。销售 Agent 上线后最危险的问题之一就是虚构价格、客户、效果承诺。

**我是如何发现并修改的：**

我设计了 `case_004_price_no_fabrication` 和 `case_006_customer_reference`，把 `¥`、`人民币`、`保证`、`海尔是我们的客户`、`富士康是我们的客户` 等词设为 forbidden_terms。最终策略改为先查知识库，不能确认时转为澄清或人工跟进。

### 错误 3

**AI 建议：**

AI 初版倾向于让真实 LLM 直接决定是否调用工具。

**为什么不对：**

这样会导致评测不稳定，同一个 case 可能因为模型采样或措辞差异出现不同工具轨迹，难以保证 12 个 eval case 可复现通过。

**我是如何发现并修改的：**

我在设计 eval runner 时意识到工具顺序是评分重点，所以把工具路由和状态迁移全部做成确定性逻辑，只把 OpenAI 放在最终 message rewrite 层。

### 错误 4

**AI 建议：**

AI 曾建议 Demo 意图出现时直接预约。

**为什么不对：**

如果没有邮箱，系统无法发送邀请，也不应该声称“已经预约成功”。

**我是如何发现并修改的：**

我加入了 `case_003_demo_missing_email`，要求缺少邮箱时 forbidden tool 包含 `book_demo`，expected_state 为 `demo_status=blocked` 和 `next_action=ask_for_email`。修复后 Agent 会先索要邮箱。

## 7. 最终反思

### 如果再多 2 小时，我会继续改进什么：

- 增加更多真实业务 case，例如竞争对手比较、用户只给电话不留邮箱、销售经理要求批量导入 lead、用户跨时区改期等。
- 把 mock CRM 和 calendar 替换成更接近真实 API 的接口层，验证失败重试和异常处理。
- 让 Excel 报告包含每个 case 的 assistant message、工具轨迹和失败原因，方便非技术同学直接审阅。
- 增加 prompt version 对比，让不同系统提示词可以在同一套 eval 上横向比较。
- 对 Langfuse trace 增加 session 维度，把一次多轮销售对话串起来看。

### 如果这个 Agent 要上线，我最担心什么：

- 最担心的是幻觉和越权承诺，尤其是价格、客户案例、合同条款、ROI 效果这几类内容。
- 第二个担心是工具调用失败时的兜底逻辑，例如日历不可用、CRM 写入失败、人工接管接口失败时，Agent 不能假装已经完成。
- 第三个担心是评测集覆盖不足。现在 12 个 case 能证明核心流程可行，但线上用户表达会更复杂，需要持续收集失败样例并扩展 eval。
- 第四个担心是隐私和数据合规。真实销售对话可能包含邮箱、公司信息、采购流程和合同需求，上线前需要明确日志脱敏、权限控制和数据保留策略。

