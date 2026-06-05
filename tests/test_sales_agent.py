"""Integration tests — require ANTHROPIC_API_KEY."""

import unittest

from sales_agent_harness.runner import AgentRunner
from sales_agent_harness.eval_runner import REQUIRED_STATE_KEYS, fixed_rule_scores


def tool_names(output: dict) -> list[str]:
    return [call["tool_name"] for call in output["tool_calls"]]


class SalesAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = AgentRunner()

    def test_demo_booking_flow(self):
        output = self.runner.run(
            "L-DEMO",
            [{"role": "user", "content": "我们想下周安排一个 Demo，我在新加坡，邮箱是 alex@demo.com。"}],
        ).to_dict()
        names = tool_names(output)
        self.assertIn("get_lead_context", names)
        self.assertIn("check_calendar", names)
        self.assertIn("book_demo", names)
        self.assertIn("write_crm_note", names)
        self.assertLess(names.index("check_calendar"), names.index("book_demo"))
        self.assertLess(names.index("book_demo"), names.index("write_crm_note"))
        self.assertEqual(output["state"]["demo_status"], "booked")
        self.assertTrue(output["state"]["demo_booked"])
        self.assertTrue(output["state"]["crm_updated"])

    def test_price_no_fabrication(self):
        output = self.runner.run(
            "L123",
            [{"role": "user", "content": "价格多少？能不能保证一个月 ROI 翻倍？"}],
        ).to_dict()
        self.assertIn("search_knowledge_base", tool_names(output))
        msg = output["assistant_message"]
        for term in ("¥", "人民币", "翻倍没问题", "保证"):
            self.assertNotIn(term, msg)

    def test_contract_handoff(self):
        output = self.runner.run(
            "L123",
            [{"role": "user", "content": "采购要看合同和数据处理协议，请销售顾问联系我。"}],
        ).to_dict()
        self.assertIn("handoff_to_human", tool_names(output))
        self.assertTrue(output["state"]["handoff_required"])
        self.assertTrue(output["state"]["crm_updated"])

    def test_demo_without_email_blocked(self):
        output = self.runner.run(
            "L-DEMO",
            [{"role": "user", "content": "我们想安排一个 Demo，下周都可以。"}],
        ).to_dict()
        self.assertNotIn("book_demo", tool_names(output))
        self.assertNotEqual(output["state"]["demo_status"], "booked")

    def test_stable_output_schema(self):
        output = self.runner.run(
            "L-NEW",
            [{"role": "user", "content": "你好，我想了解一下你们能做什么。"}],
        ).to_dict()
        self.assertTrue(REQUIRED_STATE_KEYS.issubset(output["state"].keys()))
        self.assertIn("assistant_message", output)
        self.assertIn("tool_calls", output)

    def test_eval_scores_demo_case(self):
        case = {
            "id": "demo",
            "name": "demo",
            "lead_id": "L-DEMO",
            "conversation": [
                {"role": "user", "content": "我在上海，想预约 Demo，邮箱 cn-buyer@example.com。"}
            ],
            "expected_tools": ["get_lead_context", "check_calendar", "book_demo", "write_crm_note"],
            "expected_state": {"demo_status": "booked", "crm_updated": True},
        }
        output = self.runner.run(case["lead_id"], case["conversation"]).to_dict()
        scores, _ = fixed_rule_scores(case, output)
        self.assertEqual(scores["tool_correctness"], 1.0)
        self.assertEqual(scores["state_correctness"], 1.0)


if __name__ == "__main__":
    unittest.main()
