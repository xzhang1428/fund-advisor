"""Risk tolerance assessment and profile management."""

from typing import Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config.settings import RiskProfile, RISK_ALLOCATIONS


class RiskProfiler:
    """Assess user risk tolerance through questionnaire or direct input."""

    # Risk assessment questionnaire
    QUESTIONS = [
        {
            "id": "time_horizon",
            "question": "您的投资期限是多久？",
            "options": [
                ("短期（1年以内）", 10),
                ("中短期（1-3年）", 25),
                ("中期（3-5年）", 50),
                ("长期（5-10年）", 75),
                ("超长期（10年以上）", 100),
            ],
        },
        {
            "id": "income_stability",
            "question": "您的收入稳定性如何？",
            "options": [
                ("非常不稳定（自由职业/创业初期）", 10),
                ("不太稳定（周期性行业）", 30),
                ("比较稳定（一般上班族）", 60),
                ("非常稳定（公务员/国企/体制内）", 100),
            ],
        },
        {
            "id": "loss_tolerance",
            "question": "如果您的投资组合亏损20%，您会怎么做？",
            "options": [
                ("立即全部卖出，无法承受亏损", 10),
                ("卖出一部分，减少风险敞口", 30),
                ("继续持有，等待回本", 60),
                ("逢低加仓，看好长期机会", 100),
            ],
        },
        {
            "id": "investment_knowledge",
            "question": "您的投资知识和经验如何？",
            "options": [
                ("几乎没有，刚开始了解", 10),
                ("了解基本概念，有一些经验", 35),
                ("比较熟悉，有多年的投资经历", 65),
                ("非常专业，深入研究过投资", 100),
            ],
        },
        {
            "id": "return_expectation",
            "question": "您期望的年化收益率是多少？",
            "options": [
                ("保值即可（3%-5%）", 10),
                ("稳健增值（5%-8%）", 35),
                ("较高收益（8%-15%）", 65),
                ("追求高收益（15%以上，承受高风险）", 100),
            ],
        },
        {
            "id": "liquidity_need",
            "question": "您对资金流动性的需求如何？",
            "options": [
                ("随时可能需要用钱", 10),
                ("半年内可能用到部分资金", 30),
                ("1-2年内基本不需要动用", 60),
                ("长期不需要动用", 100),
            ],
        },
    ]

    @classmethod
    def run_questionnaire(cls) -> dict:
        """Run interactive risk assessment questionnaire. Returns results dict."""
        print("\n" + "=" * 60)
        print("  风险承受能力评估问卷")
        print("=" * 60)
        print()

        answers = {}
        for q in cls.QUESTIONS:
            print(f"  {q['question']}")
            for i, (text, score) in enumerate(q["options"], 1):
                print(f"    {i}. {text}")
            choice = input("  请选择 (1-4): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(q["options"]):
                    answers[q["id"]] = {
                        "choice": q["options"][idx][0],
                        "score": q["options"][idx][1],
                    }
                else:
                    answers[q["id"]] = {"choice": "默认", "score": 50}
            except ValueError:
                answers[q["id"]] = {"choice": "默认", "score": 50}
            print()

        # Calculate total score
        total_score = sum(a["score"] for a in answers.values())
        avg_score = total_score / len(answers)

        # Map to risk profile
        if avg_score <= 30:
            profile = RiskProfile.CONSERVATIVE
        elif avg_score <= 50:
            profile = RiskProfile.MODERATE
        elif avg_score <= 75:
            profile = RiskProfile.BALANCED
        else:
            profile = RiskProfile.AGGRESSIVE

        allocation = RISK_ALLOCATIONS.get(profile.value, RISK_ALLOCATIONS["稳健型"])

        print("=" * 60)
        print(f"  评估结果: {profile.value}")
        print(f"  综合得分: {avg_score:.0f}/100")
        print()
        print("  建议资产配置:")
        for cat, weight in allocation.items():
            if weight > 0:
                bar = "#" * int(weight * 40)
                print(f"    {cat}: {bar} {weight:.0%}")
        print("=" * 60)

        return {
            "profile": profile.value,
            "score": avg_score,
            "answers": answers,
            "allocation": allocation,
        }

    @classmethod
    def get_allocation_template(cls, profile: str) -> dict:
        """Get default allocation template for a risk profile."""
        return RISK_ALLOCATIONS.get(profile, RISK_ALLOCATIONS["稳健型"])

    @classmethod
    def profile_description(cls, profile: str) -> str:
        """Get human-readable description of a risk profile."""
        descriptions = {
            "保守型": "以保本为首要目标，适合风险承受能力较低的投资者。"
                     "主要配置货币基金和债券基金，少量配置混合基金。",
            "稳健型": "在控制风险的前提下追求适度增值，适合大多数投资者。"
                     "均衡配置各类资产，股债比例大致为1:1。",
            "平衡型": "愿意承担中等风险以获取较高收益，适合有一定投资经验的投资者。"
                     "权益类资产占比可达60-70%。",
            "进取型": "追求高收益，能够承受较大波动，适合经验丰富的积极投资者。"
                     "权益类资产占比可达80%以上，可配置QDII分散风险。",
        }
        return descriptions.get(profile, "未知风险偏好")
