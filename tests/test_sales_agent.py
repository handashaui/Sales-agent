import unittest

from sales_agent_harness.agent import SalesAgent
from sales_agent_harness.eval_runner import REQUIRED_STATE_KEYS, fixed_rule_scores


def tool_names(output):
    return [call["tool_name"] for call in output["tool_calls"]]


class SalesAgentTests(unittest.TestCase):
    def test_demo_booking_flow_uses_calendar_booking_and_crm(self):
        output = SalesAgent().run(
            "L-DEMO",
            [
                {
                    "role": "user",
                    "content": "我们想下周安排一个 Demo，我在新加坡，邮箱是 alex@demo.com。",
                }
            ],
        ).to_dict()

        self.assertEqual(
            tool_names(output),
            [
                "get_lead_context",
                "check_calendar",
                "book_demo",
                "write_crm_note",
            ],
        )
        self.assertEqual(output["state"]["demo_status"], "booked")
        self.assertTrue(output["state"]["crm_updated"])

    def test_price_question_does_not_fabricate_and_updates_crm(self):
        output = SalesAgent().run(
            "L123",
            [{"role": "user", "content": "价格多少？能不能保证一个月 ROI 翻倍？"}],
        ).to_dict()

        self.assertIn("search_knowledge_base", tool_names(output))
        self.assertIn("write_crm_note", tool_names(output))
        self.assertNotIn("¥", output["assistant_message"])
        self.assertEqual(output["state"]["next_action"], "clarify_or_handoff")

    def test_contract_request_hands_off_to_human(self):
        output = SalesAgent().run(
            "L123",
            [{"role": "user", "content": "采购要看合同和数据处理协议，请销售顾问联系我。"}],
        ).to_dict()

        self.assertIn("handoff_to_human", tool_names(output))
        self.assertTrue(output["state"]["handoff_required"])
        self.assertTrue(output["state"]["crm_updated"])

    def test_output_has_stable_state_schema(self):
        output = SalesAgent().run(
            "L-NEW",
            [{"role": "user", "content": "你好，我想了解一下你们能做什么。"}],
        ).to_dict()

        self.assertTrue(REQUIRED_STATE_KEYS.issubset(output["state"].keys()))

    def test_fixed_rule_scores_accept_expected_demo_case(self):
        case = {
            "id": "demo",
            "name": "demo",
            "lead_id": "L-DEMO",
            "conversation": [
                {
                    "role": "user",
                    "content": "我在上海，想预约 Demo，邮箱 cn-buyer@example.com。",
                }
            ],
            "expected_tools": [
                "get_lead_context",
                "check_calendar",
                "book_demo",
                "write_crm_note",
            ],
            "expected_state": {"demo_status": "booked", "crm_updated": True},
        }
        output = SalesAgent().run(case["lead_id"], case["conversation"]).to_dict()
        scores, _ = fixed_rule_scores(case, output)

        self.assertEqual(scores["overall_fixed"], 1.0)


if __name__ == "__main__":
    unittest.main()
