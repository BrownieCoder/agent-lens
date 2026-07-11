# Agent Lens portfolio kit

## Resume bullet

Built and open-sourced Agent Lens, an eval-first observability dashboard for LLM workflows with structured scoring, Prompt regression testing, cost and latency analytics, and validated OpenAI/DeepSeek evaluator support; shipped with FastAPI, React, SQLite, automated tests, CI, and security documentation.

## Short project description

Agent Lens helps teams determine whether a Prompt or model change actually improved an LLM workflow. It logs runs, applies a consistent evaluation rubric, compares versions, tracks operational trade-offs, and turns difficult examples into a reusable regression set.

## Interview talking points

1. **Problem framing:** LLM output quality is subjective, so changes often optimize for length or style rather than decision usefulness.
2. **Product loop:** Run logging → structured evaluation → version comparison → regression case → Prompt decision.
3. **Architecture choice:** FastAPI, SQLAlchemy, SQLite, React, and Recharts keep the first release inspectable and locally runnable.
4. **Evaluator design:** Mock evaluation enables deterministic tests; OpenAI uses strict JSON Schema; DeepSeek uses JSON mode plus Pydantic validation.
5. **Reliability:** Malformed provider output is rejected, provider failure becomes HTTP 502, and no invalid evaluation is persisted.
6. **Trade-off:** The alpha favors a complete vertical slice over tracing infrastructure, authentication, and multi-tenancy.
7. **Next step:** Calibrate LLM judges against human labels and add pairwise experiments with statistical confidence.

## LinkedIn launch draft

I built and open-sourced **Agent Lens**, a lightweight evaluation and observability dashboard for LLM workflows.

The question behind it is simple: when you change a Prompt or model, did the output actually improve—or did it merely become longer and more confident?

Agent Lens logs workflow runs, scores output quality across evidence, risk coverage, specificity, and actionability, compares Prompt versions against cost and latency, and turns hard examples into regression cases.

The first public alpha includes:

- FastAPI + SQLAlchemy + SQLite backend
- React + TypeScript dashboard
- Mock, OpenAI, and DeepSeek evaluators
- Prompt comparison and regression workflows
- Markdown summary export
- Tests, CI, security guidance, and a one-command local workflow

Repository: https://github.com/BrownieCoder/agent-lens

I built the first use case around AI-generated financial research reports, but the architecture is generic enough for document summarization, legal workflows, and internal AI tools.

Feedback is welcome—especially from people working on LLM evaluation, AgentOps, or Prompt regression testing.

## 60-second demo flow

1. Open the overview and show the quality, cost, and latency trends.
2. Point out the `v2` versus `v1` score difference and operational trade-off.
3. Open a low-scoring run and explain the evidence and risk flags.
4. Open the regression page and explain paired inputs across Prompt versions.
5. End on the provider abstraction and `make check` release gate.
