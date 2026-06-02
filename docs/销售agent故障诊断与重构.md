# 问题诊断
对话A：主要问题是完全忽略工具调用（search_knowledge_base），全部是模型的幻觉输出，缺少clarify过程，并且问到报价应该转人工
对话B：同样是缺少clarify过程，没有调用工具(write_crm_note),并且可能对预算太依赖，没有预算直接就结束对话了
对话C：没有clarify demo的参会目的， 时区有问题，应该是Singapore而不是上海，check_calender没有给用户候选时间而是直接自己选了一个时间，没有调用book_demo真正预约，还把已预约写入了CRM

感觉问题应该要么是system prompt没写清楚clarification和toolcalling的流程，要不然就是用的模型太差了
# 设计改进方案
[sales system prompt](sales%20system%20prompt.md)
[tool use strategy](tool%20use%20strategy.md)
[test examples](test%20examples.md)
[prompt iteration](prompt%20iteration.md)
