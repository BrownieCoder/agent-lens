import json
import re
from dataclasses import dataclass

from ..config import Settings
from ..models.run import WorkflowRun
from ..schemas.evaluation import EvaluationPayload


EVALUATOR_SYSTEM_PROMPT = """You are a conservative evaluator of AI-generated research reports.
Do not reward length. Reward specificity, verifiable evidence, explicit risk coverage, calibrated
language, and decision usefulness. Penalize vague filler and unsupported claims. Score every
dimension from 1 to 5 and return JSON matching the supplied schema exactly.
"""


def _clamp(value: float) -> float:
    return round(max(1.0, min(5.0, value)), 1)


@dataclass
class EvaluationResult:
    payload: EvaluationPayload
    evaluator_type: str
    evaluator_model: str


class ProviderEvaluationError(RuntimeError):
    """A provider failed to return a valid evaluation."""


class MockEvaluator:
    """Deterministic heuristic evaluator for local development and tests."""

    version = "mock-v1"

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        text = run.output_text.strip()
        lower = text.lower()
        words = re.findall(r"\b\w+\b", text)
        has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?%?\b", text))
        evidence_terms = ("source", "according", "reported", "filing", "data", "evidence", "引用", "数据显示")
        risk_terms = ("risk", "downside", "uncertain", "however", "风险", "不确定", "下行")
        action_terms = ("monitor", "watch", "consider", "next", "关注", "建议", "观察")
        generic_terms = ("in conclusion", "it is important", "值得注意", "综上所述")
        overconfident_terms = ("guaranteed", "definitely", "will certainly", "必然", "保证")

        length_factor = min(len(words) / 180, 1.0)
        clarity = _clamp(2.0 + length_factor + (0.5 if len(text.splitlines()) >= 3 else 0))
        evidence = _clamp(1.5 + (1.2 if has_numbers else 0) + (1.0 if any(t in lower for t in evidence_terms) else 0))
        risks = _clamp(1.5 + (2.0 if any(t in lower for t in risk_terms) else 0))
        specificity = _clamp(1.5 + (1.3 if has_numbers else 0) + min(len(set(words)) / 150, 1.0))
        actionability = _clamp(1.5 + (1.7 if any(t in lower for t in action_terms) else 0))
        novelty = _clamp(1.8 + min(len(set(w.lower() for w in words)) / 180, 1.5))
        too_generic = len(words) < 45 or any(term in lower for term in generic_terms)
        weak_evidence = evidence < 3
        missing_risks = risks < 3
        overconfident = any(term in lower for term in overconfident_terms)
        possible_hallucination = overconfident and weak_evidence
        scores = [clarity, evidence, risks, specificity, actionability, novelty]
        overall = _clamp(sum(scores) / len(scores) - (0.3 if too_generic else 0))
        needs_review = possible_hallucination or run.status != "success" or overall < 2.5

        comments = (
            f"Deterministic mock evaluation: {len(words)} words; "
            f"numeric specificity={'present' if has_numbers else 'absent'}; "
            f"risk coverage={'present' if not missing_risks else 'weak'}."
        )
        payload = EvaluationPayload(
            clarity_score=clarity,
            evidence_score=evidence,
            risk_coverage_score=risks,
            specificity_score=specificity,
            actionability_score=actionability,
            novelty_score=novelty,
            overall_score=overall,
            possible_hallucination=possible_hallucination,
            too_generic=too_generic,
            missing_risks=missing_risks,
            overconfident_language=overconfident,
            weak_evidence=weak_evidence,
            needs_human_review=needs_review,
            comments=comments,
        )
        return EvaluationResult(payload, "mock", self.version)


class OpenAIEvaluator:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for the OpenAI evaluator")
        self.settings = settings

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        from openai import OpenAI

        try:
            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.responses.create(
                model=self.settings.openai_evaluator_model,
                instructions=EVALUATOR_SYSTEM_PROMPT,
                input=(
                    f"Workflow: {run.workflow_name}\nSource type: {run.source_type}\n\n"
                    f"INPUT:\n{run.input_text}\n\nOUTPUT TO EVALUATE:\n{run.output_text}"
                ),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "workflow_evaluation",
                        "strict": True,
                        "schema": EvaluationPayload.model_json_schema(),
                    }
                },
            )
            payload = EvaluationPayload.model_validate_json(response.output_text)
        except Exception as exc:
            raise ProviderEvaluationError("OpenAI did not return a valid evaluation") from exc
        return EvaluationResult(payload, "llm", self.settings.openai_evaluator_model)


class DeepSeekEvaluator:
    """DeepSeek Chat Completions evaluator using JSON Output mode."""

    def __init__(self, settings: Settings):
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for the DeepSeek evaluator")
        self.settings = settings

    def evaluate(self, run: WorkflowRun) -> EvaluationResult:
        from openai import OpenAI

        schema_example = json.dumps(
            {
                key: (False if prop.get("type") == "boolean" else "brief explanation" if key == "comments" else 1)
                for key, prop in EvaluationPayload.model_json_schema()["properties"].items()
            },
            ensure_ascii=False,
        )
        system_prompt = (
            f"{EVALUATOR_SYSTEM_PROMPT}\nReturn JSON only. Every field is required. "
            f"Use exactly this JSON shape: {schema_example}"
        )
        try:
            client = OpenAI(api_key=self.settings.deepseek_api_key, base_url=self.settings.deepseek_base_url)
            response = client.chat.completions.create(
                model=self.settings.deepseek_evaluator_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            f"Workflow: {run.workflow_name}\nSource type: {run.source_type}\n\n"
                            f"INPUT:\n{run.input_text}\n\nOUTPUT TO EVALUATE:\n{run.output_text}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=2000,
                extra_body={"thinking": {"type": "disabled"}},
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("DeepSeek returned empty content")
            payload = EvaluationPayload.model_validate_json(content)
        except Exception as exc:
            raise ProviderEvaluationError("DeepSeek did not return a valid evaluation") from exc
        return EvaluationResult(payload, "llm", self.settings.deepseek_evaluator_model)


def get_evaluator(name: str, settings: Settings):
    if name == "openai":
        return OpenAIEvaluator(settings)
    if name == "mock":
        return MockEvaluator()
    if name == "deepseek":
        return DeepSeekEvaluator(settings)
    raise ValueError(f"Unsupported evaluator backend: {name}")
