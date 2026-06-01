"""Sales agent harness with deterministic stateful behavior."""

from __future__ import annotations

import re
import uuid
from typing import Any

from .models import AgentOutput, AgentState, ConversationTurn, ToolCallRecord
from .prompts import get_system_prompt
from .tools import MockToolRuntime

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


class SalesAgent:
    """Minimal DeerFlow-style agent harness for sales lead follow-up."""

    def __init__(
        self,
        tool_runtime: MockToolRuntime | None = None,
        prompt_version: str = "v1",
        model: str | None = None,
        prefer_real_llm: bool = True,
    ) -> None:
        self.tool_runtime = tool_runtime or MockToolRuntime()
        self.prompt_version = prompt_version
        self.model = model
        self.prefer_real_llm = prefer_real_llm
        self.system_prompt = get_system_prompt(prompt_version)

    def run(
        self,
        lead_id: str,
        conversation: list[dict[str, str]] | list[ConversationTurn],
        prior_state: AgentState | None = None,
        run_id: str | None = None,
    ) -> AgentOutput:
        state = prior_state or AgentState()
        state.run_id = run_id or state.run_id or str(uuid.uuid4())
        turns = [
            turn if isinstance(turn, ConversationTurn) else ConversationTurn(**turn)
            for turn in conversation
        ]
        transcript = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)
        latest_user = next(
            (turn.content for turn in reversed(turns) if turn.role == "user"), ""
        )

        tool_calls: list[ToolCallRecord] = []
        if not state.lead_context:
            context = self._call_tool(
                state, tool_calls, "get_lead_context", {"lead_id": lead_id}
            )
            state.lead_context = context

        facts = self._extract_facts(transcript)
        state.qualification_level = self._qualify(facts, transcript)
        state.missing_info = self._missing_info(facts, transcript)

        if self._needs_handoff(latest_user, transcript):
            reason = self._handoff_reason(latest_user, transcript)
            self._call_tool(
                state,
                tool_calls,
                "handoff_to_human",
                {"lead_id": lead_id, "reason": reason, "priority": "high"},
            )
            state.handoff_required = True
            state.next_action = "handoff_to_human"
            state.risk_flags.append(reason)
            message = (
                "这个问题需要销售顾问人工确认，我已经为你转接。"
                "在人工跟进前，我不会编造价格、客户案例或合同承诺。"
            )
            self._write_followup_note(lead_id, state, "Human handoff requested")
            return AgentOutput(message, tool_calls, state)

        if self._asks_sensitive_claim(latest_user):
            self._call_tool(
                state,
                tool_calls,
                "search_knowledge_base",
                {"query": latest_user},
            )
            state.next_action = "clarify_or_handoff"
            state.risk_flags.append("no_fabricated_claims")
            message = (
                "我不能直接给出未确认的价格、客户案例或承诺。"
                "我可以先基于你们的场景整理需求，并安排销售顾问确认准确方案。"
            )
            self._write_followup_note(lead_id, state, "Sensitive claim avoided")
            return AgentOutput(message, tool_calls, state)

        if self._wants_demo(transcript):
            return self._handle_demo(lead_id, latest_user, transcript, state, tool_calls)

        if self._has_business_context(transcript):
            self._call_tool(
                state,
                tool_calls,
                "search_knowledge_base",
                {"query": self._knowledge_query(transcript)},
            )
            state.next_action = "continue_qualification"
            self._write_followup_note(
                lead_id,
                state,
                "Lead qualified for consultative follow-up",
                tool_calls,
            )
            question = self._next_clarifying_question(state.missing_info)
            message = (
                "听起来你们的核心问题是线索响应不及时和漏跟进。"
                "AI 可以先从线索优先级、自动提醒、CRM 记录和下一步建议做起。"
                f"{question}"
            )
            return AgentOutput(message, tool_calls, state)

        state.next_action = "clarify"
        message = (
            "可以，我先帮你判断是否适合用 AI 做销售跟进。"
            "请问你们公司规模、销售团队人数，以及现在最常漏掉的是哪类线索？"
        )
        return AgentOutput(message, tool_calls, state)

    def _call_tool(
        self,
        state: AgentState,
        visible_calls: list[ToolCallRecord],
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        result = self.tool_runtime.registry()[tool_name](**arguments)
        record = ToolCallRecord(tool_name=tool_name, arguments=arguments, result=result)
        visible_calls.append(record)
        state.trajectory.append(record)
        return result

    def _write_followup_note(
        self,
        lead_id: str,
        state: AgentState,
        summary: str,
        visible_calls: list[ToolCallRecord] | None = None,
    ) -> None:
        visible_calls = visible_calls if visible_calls is not None else []
        self._call_tool(
            state,
            visible_calls,
            "write_crm_note",
            {
                "lead_id": lead_id,
                "summary": summary,
                "qualification_level": state.qualification_level,
                "next_action": state.next_action,
            },
        )
        state.crm_updated = True

    def _handle_demo(
        self,
        lead_id: str,
        latest_user: str,
        transcript: str,
        state: AgentState,
        tool_calls: list[ToolCallRecord],
    ) -> AgentOutput:
        email = self._extract_email(transcript)
        timezone_name = self._extract_timezone(transcript)
        if not email:
            state.demo_status = "blocked"
            state.next_action = "ask_for_email"
            state.missing_info = sorted(set(state.missing_info + ["email"]))
            message = "可以安排 Demo。请发我你的邮箱，我就帮你查询可预约时间。"
            return AgentOutput(message, tool_calls, state)

        calendar = self._call_tool(
            state,
            tool_calls,
            "check_calendar",
            {"timezone_name": timezone_name, "duration_minutes": 30},
        )
        slot = calendar["available_slots"][0]
        booking = self._call_tool(
            state,
            tool_calls,
            "book_demo",
            {
                "lead_id": lead_id,
                "slot_id": slot["slot_id"],
                "email": email,
                "timezone_name": timezone_name,
            },
        )
        state.demo_status = "booked"
        state.next_action = "demo_booked"
        state.qualification_level = (
            "high" if state.qualification_level in {"medium", "high"} else "medium"
        )
        self._write_followup_note(
            lead_id,
            state,
            f"Demo booked for {slot['label']} with {email}",
            tool_calls,
        )
        message = (
            f"好的，已为你安排 {slot['label']} 的 Demo，邀请会发送到 {email}。"
            f"预约编号是 {booking['booking_id']}。"
        )
        return AgentOutput(message, tool_calls, state)

    def _extract_facts(self, transcript: str) -> dict[str, Any]:
        numbers = [int(num) for num in re.findall(r"\d+", transcript)]
        return {
            "numbers": numbers,
            "email": self._extract_email(transcript),
            "has_company": any(
                term in transcript
                for term in ["公司", "企业", "manufacturing", "制造", "SaaS"]
            ),
            "has_sales_team": any(
                term in transcript for term in ["销售团队", "销售", "sales team"]
            ),
            "has_pain": any(
                term in transcript
                for term in ["漏", "不及时", "跟进", "线索", "lead", "response"]
            ),
        }

    def _qualify(self, facts: dict[str, Any], transcript: str) -> str:
        score = 0
        if facts["has_company"]:
            score += 1
        if facts["has_sales_team"]:
            score += 1
        if facts["has_pain"]:
            score += 1
        if self._wants_demo(transcript):
            score += 2
        if any(num >= 100 for num in facts["numbers"]):
            score += 1
        if score >= 4:
            return "high"
        if score >= 2:
            return "medium"
        if "学生" in transcript or "作业" in transcript:
            return "low"
        return "unknown"

    def _missing_info(self, facts: dict[str, Any], transcript: str) -> list[str]:
        missing = []
        if not facts["has_company"]:
            missing.append("company_profile")
        if not facts["has_sales_team"]:
            missing.append("sales_team_size")
        if not facts["has_pain"]:
            missing.append("pain_point")
        if self._wants_demo(transcript) and not facts["email"]:
            missing.append("email")
        return missing

    def _has_business_context(self, transcript: str) -> bool:
        return any(
            term in transcript
            for term in ["公司", "销售", "线索", "客户", "制造", "CRM", "AI", "lead"]
        )

    def _wants_demo(self, transcript: str) -> bool:
        return any(term in transcript.lower() for term in ["demo", "演示", "预约", "安排"])

    def _needs_handoff(self, latest_user: str, transcript: str) -> bool:
        handoff_terms = [
            "人工",
            "真人",
            "销售顾问",
            "合同",
            "法务",
            "采购",
            "安全审计",
            "数据处理协议",
            "dpa",
            "msa",
        ]
        return any(term in latest_user.lower() for term in handoff_terms)

    def _handoff_reason(self, latest_user: str, transcript: str) -> str:
        if any(term in latest_user for term in ["人工", "真人", "销售顾问"]):
            return "user_requested_human"
        return "requires_human_commitment"

    def _asks_sensitive_claim(self, latest_user: str) -> bool:
        terms = [
            "价格",
            "报价",
            "多少钱",
            "保证",
            "承诺",
            "客户案例",
            "竞品",
            "roi",
            "sla",
            "pricing",
            "reference",
        ]
        return any(term in latest_user.lower() for term in terms)

    def _extract_email(self, transcript: str) -> str | None:
        match = EMAIL_RE.search(transcript)
        return match.group(0) if match else None

    def _extract_timezone(self, transcript: str) -> str:
        if any(term in transcript for term in ["新加坡", "Singapore", "SGT"]):
            return "Asia/Singapore"
        if any(term in transcript for term in ["上海", "中国", "北京时间", "CST"]):
            return "Asia/Shanghai"
        return "Asia/Shanghai"

    def _knowledge_query(self, transcript: str) -> str:
        if "制造" in transcript:
            return "manufacturing lead follow-up AI sales CRM"
        return "sales lead follow-up AI CRM"

    def _next_clarifying_question(self, missing: list[str]) -> str:
        if "company_profile" in missing:
            return "你们大概是什么行业和公司规模？"
        if "sales_team_size" in missing:
            return "销售团队大概多少人？"
        if "pain_point" in missing:
            return "目前最影响转化的是响应慢、分配慢，还是 CRM 记录不完整？"
        return "如果方便，我想确认你们希望先做自动提醒、线索评分，还是直接预约 Demo？"
