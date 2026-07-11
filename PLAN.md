# Agent Lens MVP 实施计划

本文档是项目落地的权威进度记录。每完成一项，都同步更新状态、实现细节、验证结果和可优化方向。

状态说明：`待开始`、`进行中`、`已完成`。

## 进度总览

| # | 工作项 | 状态 |
|---|---|---|
| 1 | 建立 MVP 实施计划 | 已完成 |
| 2 | FastAPI + SQLite 数据模型与基础应用 | 已完成 |
| 3 | Run 日志 API | 已完成 |
| 4 | Mock 结构化评测 API | 已完成 |
| 5 | React Dashboard：汇总、运行列表、详情 | 已完成 |
| 6 | 示例数据 Seed | 已完成 |
| 7 | Markdown 评测报告 | 已完成 |
| 8 | 真实 OpenAI evaluator | 已完成（待配置 Key 实跑） |
| 9 | Prompt 对比与回归测试流程 | 已完成 |
| 10 | README 与端到端验证 | 已完成 |
| 11 | Public release hardening | 已完成 |

## 1. 建立 MVP 实施计划

**状态：已完成**

### 完成细节

- 确定以 `LLM 输出 → 评测 → 对比 → 决策 → Prompt 改进` 为产品主循环。
- 将后端、前端、数据、评测、报告和回归流程拆成可独立验证的交付项。
- 约定本文件与实际实现同步更新，不用“代码已写”替代运行验证。

### 验证

- `PLAN.md` 已进入项目根目录并包含全部 MVP 阶段。

### 可优化方向

- 后续可增加版本里程碑、负责人、预计工期和变更日志。
- 接入 CI 后可将验证命令和构建状态自动回写到发布记录。

## 2. FastAPI + SQLite 数据模型与基础应用

**状态：已完成**

### 目标

- 建立 FastAPI 应用、配置、数据库会话和 SQLite 默认连接。
- 建立 Run、Evaluation、RegressionCase 数据表，并为将来迁移 Postgres 保留 ORM 边界。

### 完成细节

- 建立配置层、数据库 engine/session、FastAPI lifespan 和 CORS。
- 建立 `WorkflowRun`、`Evaluation`、`RegressionCase` ORM 模型及关系。
- 数据库连接通过 `DATABASE_URL` 配置，默认使用 SQLite，ORM 不依赖 SQLite 特有查询。

### 验证

- `python -m compileall app seed.py` 通过。
- FastAPI 测试 lifespan 可创建全量 schema。

### 可优化方向

- MVP 稳定后引入 Alembic 管理 schema migration。
- 生产环境切换 Postgres，并补充连接池与数据库健康检查。

## 3. Run 日志 API

**状态：已完成**

### 目标

- 实现 `POST /runs`、`GET /runs`、`GET /runs/{id}`。
- 支持按 workflow、prompt、model、status 过滤和分页。

### 完成细节

- 实现创建、分页列表、过滤与详情接口，详情包含全部评测记录。
- 为常用维度和时间字段建立索引，输入 token/cost/latency 带非负校验。

### 验证

- API 测试验证 Run 创建、详情读取和 `prompt_version` 过滤。

### 可优化方向

- 增加批量导入、幂等键、敏感文本脱敏和对象存储。

## 4. Mock 结构化评测 API

**状态：已完成**

### 目标

- 实现 `POST /runs/{id}/evaluate` 与 `GET /runs/{id}/evaluation`。
- 使用可重复、保守的本地规则生成 1–5 分和风险 flags。

### 完成细节

- Mock evaluator 依据数字证据、风险词、行动建议、词汇多样性、泛化表达和过度自信生成分数与 flags。
- Mock 逻辑是确定性的，不因输出变长自动加高分；失败和低分运行自动进入人工复核 flag。
- 支持保留多次评测，latest evaluation 接口返回最新记录。

### 验证

- 测试验证评测分数处于 1–5，Run 详情包含评测，聚合读取最新评测。

### 可优化方向

- 增加 evaluator prompt 版本、重复评测、校准样本和人工复核队列。

## 5. React Dashboard

**状态：已完成**

### 目标

- 展示汇总指标、趋势、Prompt 对比、最近/最好/最差运行和运行详情。

### 完成细节

- 建立 React + TypeScript + Vite 前端和响应式侧边导航。
- 概览页展示 KPI、质量/延迟趋势、Prompt 表格、最近/最好/最差运行。
- Run explorer 支持前端过滤；详情页展示元数据、各维度分数、flags、评论与输入输出。
- 增加独立 Prompt comparison 和 Regression cases 页面。

### 验证

- `npm run build` 通过（Vite 6.4.3，626 modules transformed）。
- 浏览器验证概览、Run #24 详情、Prompt 对比和 Regression 页面均正常渲染，API 返回 200。

### 可优化方向

- 增加筛选器、下钻、置信区间、可访问性和移动端布局。

## 6. 示例数据 Seed

**状态：已完成**

### 目标

- 生成至少 20 条 x-signal 风格运行，覆盖两个 Prompt 版本、成功/失败和不同质量区间。

### 完成细节

- `seed.py` 固定随机种子，创建 12 个 regression cases、24 条成对样本及对应 Mock evaluations。
- 样本覆盖四种来源、`v1`/`v2`、成功/超时、不同 token/cost/latency。
- Seed 对已有数据默认跳过，避免误覆盖用户数据。

### 验证

- 在独立验证数据库中实际生成 12 个 cases、24 条 Run，且 24 条全部关联 case；v1/v2 各 12 条。

### 可优化方向

- 替换为去标识化真实样本，并提供 CSV/JSON 导入器。

## 7. Markdown 评测报告

**状态：已完成**

### 目标

- 实现日期范围内的质量、成本、延迟、版本表现、失败模式与建议汇总。

### 完成细节

- `POST /reports/evaluation-summary` 输出 Markdown。
- 报告包含日期范围、KPI、Prompt 排名、常见 flags 以及基于失败模式生成的行动建议。

### 验证

- API 测试确认响应包含 `Agent Lens Evaluation Summary` 且 Prompt 聚合可读。

### 可优化方向

- 增加模板定制、定时生成、PDF 和 Slack/邮件分发。

## 8. 真实 OpenAI evaluator

**状态：已完成（待配置 Key 实跑）**

### 目标

- 在保持 Mock 可用的同时，通过配置切换真实 evaluator。
- 强制结构化 JSON 输出，并记录 evaluator 模型和版本。

### 完成细节

- 实现基于 Responses API 的 `OpenAIEvaluator`，通过 `EVALUATOR_BACKEND` 或单次请求切换。
- 使用 strict JSON Schema；Pydantic schema 禁止额外字段并要求全部 score/flag 字段。
- 持久化 evaluator 类型、模型、分数、flags、评论和时间。
- 调用形态已依据 OpenAI 官方 Responses API `text.format: json_schema` 文档核对。

### 验证

- 本地 OpenAI SDK 方法签名确认支持 `instructions`、`input`、`text` 和 Responses API 返回值。
- 单元测试确认 JSON Schema 为 `additionalProperties: false` 且所有属性均 required。
- 因仓库未配置 `OPENAI_API_KEY`，未产生真实付费 API 调用；配置 Key 后可直接实跑。

### 可优化方向

- 增加多模型仲裁、pairwise judge、缓存、重试和成本预算。

## 9. Prompt 对比与回归测试流程

**状态：已完成**

### 目标

- 提供 Prompt 版本聚合对比。
- 实现 regression case CRUD 和记录不同 Prompt/模型运行结果的流程。

### 完成细节

- Prompt 聚合覆盖所有 7 个评分维度、运行数、成本、延迟和失败率，并只取每个 Run 最新评测。
- Regression API 支持创建、列表、详情，以及按 case 查询关联 Run。
- Run 可记录 `regression_case_id`，用相同 case 下的 Prompt/模型运行构成轻量回归对比。
- 前端支持 Prompt 对比卡片及 Regression case 创建/浏览。

### 验证

- 测试验证 regression case 创建、关联 Run 查询和 Prompt 聚合。
- 浏览器验证 v2/v1 对比数据及 Regression 表单均正常展示。

### 可优化方向

- 增加 golden answer、数据集版本、显著性检验和 CI quality gate。

## 10. README 与端到端验证

**状态：已完成**

### 目标

- 提供本地安装、启动、配置、Seed 和测试说明。
- 验证后端测试、前端构建以及关键 API 纵向链路。

### 完成细节

- README 包含项目定位、功能、后端/前端启动、环境配置、OpenAI evaluator、API、导入与验证命令。
- 固定前端依赖版本并生成 `package-lock.json`；提供 `.env.example` 与 `.gitignore`。
- 根据 `npm audit` 将 Vite 升级至修复版本 6.4.3；安装后完整审计报告为 0 vulnerabilities。

### 验证

- 后端：`3 passed`，覆盖 Run → Evaluation → Dashboard → Report 和 Regression 纵向链路。
- 前端：TypeScript + Vite production build 成功。
- 浏览器：使用 24 条实际 Seed 数据完成页面和路由冒烟检查。

### 可优化方向

- 增加一键开发命令、CI、部署文档和生产运行手册。

## 11. Public release hardening

**状态：已完成**

### 目标

- 将 MVP 整理为适合作品集展示和公开协作的 `v0.1.0-alpha`。
- 确保新用户可理解定位、快速运行、验证质量，并清楚知道安全边界。

### 已完成细节

- 取消旧的初始提交并完整保留工作区，等待 hardening 完成后重新建立发布基线。
- 增加 MIT License、贡献指南、安全策略、Changelog、Pull Request 模板和发布清单。
- 增加 Makefile 一键安装、Seed、开发、测试、构建与检查命令。
- 增加 GitHub Actions 后端测试、前端构建和依赖审计。
- README 重构为公开项目首页，突出问题、差异化、架构、快速启动和边界。
- 接入 DeepSeek JSON evaluator，默认使用当前 `deepseek-v4-flash`，并增加 provider 错误隔离。

### 完成验证

- 生成并嵌入无敏感数据的 Dashboard 全页截图。
- 根目录 `make check` 通过：7 个后端测试、Python compileall、前端 production build、0 npm vulnerabilities。
- DeepSeek JSON Output 通过 fake-provider contract test；无 Key、未知 evaluator、provider 失败路径均有测试。
- `/health` 返回 `0.1.0-alpha`，Dashboard 和 404 页面浏览器冒烟测试通过，控制台 0 errors。
- Starlette 测试客户端切换到 HTTPX2，测试输出无弃用警告。
- 前端页面改为 route-level lazy loading；入口包降至约 236 kB，Dashboard 独立约 361 kB，消除大 chunk 警告。
- 发布前仍需维护者使用自己的 OpenAI/DeepSeek Key 各执行一次真实付费 provider smoke test。

### 可优化方向

- 发布后增加录屏、在线 Demo、真实匿名案例和性能基准。
- 增加 Alembic、认证、Postgres、OpenTelemetry 和 Prompt CI quality gate。

## 12. GitHub public release execution

**状态：进行中**

### 已完成

- 确认公开仓库为 `BrownieCoder/agent-lens`，默认分支为 `main`。
- 确认首次 GitHub Actions CI 已成功完成。
- README 增加真实 clone URL、CI、License 和 alpha release badges。
- Changelog 固定 `0.1.0-alpha` 发布日期，并增加可直接用于 GitHub 的 release notes。
- 增加求职作品集文案、面试 talking points、LinkedIn 发布草稿和 60 秒演示流程。

### 进行中

- 提交并推送 release metadata 更新。
- 创建并推送 `v0.1.0-alpha` annotated tag。

### 外部设置

- GitHub About description/topics、Pre-release 和 branch protection 需要已登录的 GitHub 管理会话。
