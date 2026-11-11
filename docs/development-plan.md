# AI 后端服务开发计划

日期：2026-11-11。本文是基于当前仓库的建议方案，并非已实现功能清单。

## 1. 项目定位与现状

本项目承担 AI 能力服务职责：统一模型访问、上下文组织、Prompt / Skill 加载、Tool 执行和后续 Agent 编排。业务项目通过 HTTP 接口调用；前端可经现有业务后端转发，也可在有用户鉴权的前提下直接访问本服务。

实际检查结果：`main.py` 是 Hello 入口，README 原为空，`pyproject.toml` 尚无依赖，已有 `uv.lock`。已具备 Python 工程起点，尚未建立应用分层。现有 Git 暂存与 IDE 配置保持原样。

建议先采用模块化单体，一个服务、一个数据库；按能力建立模块，暂不拆微服务。第一版不引入向量数据库、任务队列或多 Agent 协作。知识检索、长任务等出现明确需求后再加入。

## 2. 技术选择

### 2.1 分阶段依赖

| 阶段 | 库 / 工具 | 用途与选择理由 |
| --- | --- | --- |
| P1 | `fastapi` | HTTP API、请求校验、依赖注入和 OpenAPI 文档 |
| P1 | `uvicorn[standard]` | ASGI 服务运行与本地自动重载 |
| P1 | `pydantic`、`pydantic-settings` | 内部数据结构、请求结构、环境变量配置；直接使用的包显式声明 |
| P1 | `openai` | 用 `AsyncOpenAI` 调用 Ollama / 千问的兼容接口；不意味着使用 OpenAI 的模型服务 |
| P1 | `httpx` | API 测试及后续异步 HTTP Tool；HTTP 资源通过应用生命周期统一关闭 |
| P1 开发 | `pytest`、`pytest-asyncio`、`ruff` | 核心行为测试、异步测试、格式化与静态检查 |
| P2 | `sqlalchemy[asyncio]`、`alembic` | 数据访问与数据库迁移 |
| P2 本地 | `aiosqlite` | SQLite 异步驱动，适合单机开发 |
| P2 上线 | `psycopg[binary]` | 推荐 PostgreSQL 驱动；异步模式需正确配置数据库 URL。若现有基础设施是 MySQL，再替换驱动与迁移验证 |
| P4 | `jinja2` | 仅加载仓库内可信的 Prompt 模板，缺失变量应报错 |
| 按需 | `pyyaml` | Skill 元信息选择 YAML 时再添加；第一版可用标准库 `tomllib` 读取 TOML |
| 按需 | `structlog`、OpenTelemetry 相关包 | 日志先用标准库，跨服务追踪和复杂结构化日志出现需求后再增加 |
| 按需 | `redis` | 多实例限流、短期缓存或分布式协调；不作为会话历史的唯一存储 |
| P6 按需 | `langgraph` | 有分支工作流、持久化执行、暂停恢复和人工介入需求时评估 |

保留现有 `uv`。在实施对应阶段时添加依赖，解析后提交 `uv.lock`，CI 使用 `uv sync --locked`。本次只做规划，没有安装依赖或改变锁文件。

当前 Python 为 3.14，暂保留。P1 必须在该版本验证依赖安装、启动和测试；若生产运行环境或某个所需驱动不支持，再评估统一改为 3.13，同时更新 `.python-version`、`requires-python`、锁文件和 CI。这里没有认定 3.14 存在已知兼容问题。

首期直接使用 SDK 加轻量自有接口。暂不同时引入 LangChain、LangGraph、LlamaIndex 等多个框架。若后续接入 LangGraph，将其放在编排层，外部 API 和持久化接口保持稳定；LangGraph 官方说明其不要求使用 LangChain。

### 2.2 模型供应商与配置

建议统一配置项：

| 配置项 | 语义 |
| --- | --- |
| `APP_ENV` | `development` / `test` / `production` |
| `LLM_PROVIDER` | `ollama` / `qwen`，由部署配置决定 |
| `LLM_BASE_URL` | 本地默认 `http://localhost:11434/v1`；千问按控制台业务空间和地域配置 |
| `LLM_MODEL` | 本地已安装模型名或云端已开通模型名；首期不接受客户端任意覆盖 |
| `LLM_API_KEY` | Ollama 可使用 SDK 所需的占位值；千问为真实密钥，按 Secret 管理 |
| `LLM_TIMEOUT_SECONDS` | 上游请求超时，另设整体 Run 截止时间 |
| `LLM_MAX_OUTPUT_TOKENS` | 输出预算，与模型能力配置联动 |
| `DATABASE_URL` | P2 起启用 |
| `CORS_ORIGINS` | 直接对接浏览器时配置明确来源 |
| `MAX_TOOL_ROUNDS` / `TOOL_TIMEOUT_SECONDS` | P4 起限制工具循环与单次执行 |

`.env.example` 只放占位符；P1 补充 `.env` 忽略规则，禁止密钥进入日志。生产配置缺失时启动即失败。不得由请求方提供任意上游 URL 或密钥。

依据官方文档，两端均支持 Chat Completions，Ollama 只兼容其中一部分参数。千问的 API Key 与 endpoint 必须匹配地域；当前官方文档推荐业务空间专属域名，因此上线地址应从实际控制台确认，不在代码中写死旧域名。

建立服务端模型能力配置：`supports_tools`、`supports_streaming`、`supports_structured_output`、上下文与输出预算、思考模式参数。工具可用性同时取决于运行时、模型和模板；不能从“兼容接口”推断所有能力一致。

会话由本服务维护，不依赖供应商的有状态会话 API。使用 Chat Completions 作为共同起点是本项目的架构选择，不代表供应商没有 Responses API。

## 3. 目标目录与模块边界

以下目录按阶段创建，不提前生成大量空文件：

```text
blog-server-agent/
├── pyproject.toml
├── uv.lock
├── .env.example                 # P1
├── README.md
├── docs/development-plan.md
├── src/blog_server_agent/
│   ├── main.py                  # FastAPI 工厂、生命周期、依赖装配
│   ├── api/
│   │   ├── dependencies.py      # 鉴权上下文、服务依赖
│   │   └── v1/                  # health、chat、conversations、runs 路由
│   ├── core/                    # 配置、错误码、日志、请求标识
│   ├── schemas/                 # 对外请求、响应、流事件
│   ├── domain/                  # 自有 Message、ToolCall、Run 等类型
│   ├── llm/
│   │   ├── base.py              # LLMProvider 协议、模型结果与流事件
│   │   ├── openai_compatible.py # 公共协议转换与异步调用
│   │   └── providers/           # Ollama / 千问参数与能力差异
│   ├── services/                # ChatService、上下文构造、执行协调
│   ├── repositories/            # 会话、消息、运行记录的数据访问
│   ├── db/                      # 引擎、Session、ORM 模型
│   ├── prompts/                 # Prompt 加载、渲染、版本解析
│   ├── skills/                  # Skill 元信息、允许工具、输入约束
│   ├── tools/                   # 注册表、参数模型、执行器、内置工具
│   └── agents/                  # 需要时加入执行状态机或图编排
├── resources/
│   ├── prompts/                 # 可信模板与版本元信息
│   └── skills/                  # TOML 元信息 + Markdown 指令
├── migrations/                  # P2 Alembic
└── tests/                       # provider、service、API、持久化、Tool 行为
```

调用关系：`API → Service → Provider / Repository / ToolExecutor`。路由只负责输入输出和鉴权，不直接组装供应商请求。业务服务使用自有类型，供应商 SDK 类型只在适配层转换。通过依赖注入替换 Provider 和 Repository，测试无需真实模型或云端密钥。

采用 `src` 布局时须配置构建后端及资源打包规则，验证安装后的包可以从任意工作目录加载模板，不依赖进程当前目录。模型客户端、HTTP 客户端和数据库引擎通过 FastAPI lifespan 创建及关闭。

## 4. 核心能力设计

### 4.1 会话历史与上下文

初期数据模型：

| 实体 | 关键内容 |
| --- | --- |
| Conversation | ID、所属应用和用户、标题、状态、创建时间 |
| Message | ID、会话、序号、role、content、tool_calls、tool_call_id、所属 Run |
| Run | ID、会话、幂等键、状态、供应商 / 模型、Prompt / Skill 版本、耗时、usage、错误码 |
| ToolExecution | Run、tool_call_id、工具名、脱敏参数摘要、结果摘要、状态、耗时 |

数据库保留完整历史，送给模型的上下文是按预算构造的子集。固定保留系统指令、当前输入和最近完整交互；裁剪时保持 assistant tool_calls 与对应 tool 消息完整。单条输入过长时返回明确错误，不悄悄丢弃问题。首期使用可配置的保守预算；不能把面向其他模型的 tokenizer 计数当作千问精确计数。后续根据实际 usage 校准，再考虑历史摘要。

同一会话并发生成首期拒绝为 409；多实例部署前必须使用数据库约束、租约或其他跨进程协调，不仅依赖进程内锁。数据库事务尽量短，不在一次长事务里等待模型或工具返回。

消息和 Run 应记录成功、失败、取消状态；失败的半截输出不作为完整回答重新发送给模型。重试策略需明确当前输入是否已经持久化，避免重复 user 消息。

### 4.2 Tool、Prompt、Skill 与 Agent

- **Prompt**：版本化的模型指令模板，具有变量定义与渲染校验。
- **Tool**：服务端实际执行的函数，具有名称、描述、参数 schema、权限及超时策略。
- **Skill**：本项目约定的能力包，组合 Prompt、输入要求、允许工具和执行配置；不是 Python 自带能力，也不会自动兼容任意平台的 SKILL.md。
- **Agent**：协调上下文、模型、工具和状态的执行器；初期一个有界工具循环即可。

首个 Skill 可选 `blog_outline`：输入主题、受众与风格，输出文章提纲。以纯 Prompt 验证加载机制，再与只读的 `search_articles` 工具组合；业务检索接口尚未具备时用测试替身验证，不捏造真实文章。

工具调用流程：

```text
构造上下文与授权工具列表 → 请求模型 → 若返回 tool_calls：
保存完整 assistant 消息 → 校验工具名、权限和参数 → 执行工具
→ 按 tool_call_id 追加结果 → 再请求模型 → 最终回答或触发轮数 / 时间上限
```

允许工具取“用户 / 应用权限、Skill 配置、服务端注册表”的交集。第一版只做无副作用工具：如当前时间、文章查询。参数用 Pydantic 校验；未知工具不执行；工具结果限制大小并视为外部数据处理。模型返回工具调用建议，由服务端决定是否执行。

覆盖多个 tool_calls、无效 JSON、参数不合规、超时、执行异常和最大轮数；第一版可按顺序执行。同步阻塞工具须移到线程或进程，不能阻塞事件循环；异步超时不等于已经终止外部副作用。未来发布、删除、付款等工具另加明确授权、幂等和审计机制。

### 4.3 对外 API 与前端流式协议

建议的自有接口，不直接暴露供应商请求体：

| 接口 | 阶段 | 行为 |
| --- | --- | --- |
| `GET /health/live` | P1 | 进程存活；不触发付费推理 |
| `GET /health/ready` | P2 | 配置及必要基础设施就绪，不宣称模型推理一定成功 |
| `POST /api/v1/chat` | P1 | 非流式回答；P2 后支持 conversation_id 与持久化 |
| `POST /api/v1/conversations` | P2 | 创建当前身份下的会话 |
| `GET /api/v1/conversations` | P2 | 分页列出当前身份可访问的会话 |
| `GET /api/v1/conversations/{id}/messages` | P2 | 校验归属后分页读取历史 |
| `POST /api/v1/chat/stream` | P3 | POST 输入，返回 SSE；前端使用 fetch 读取流 |
| `GET /api/v1/runs/{id}` | P3 | 查询运行状态与最终结果，处理断线后的状态确认 |

P1 最小请求为 `{"message":"你好"}`；P2 后可加 `conversation_id`；P4 后可加服务端允许的 `skill_id`。`request_id` 用于追踪；客户端幂等键用于防重复请求，两者职责不同。响应携带 Run / 会话标识、答案和可用的 usage，不伪造缺失的 token 数据。

统一错误结构包含 `code`、`message`、`request_id`；区分输入错误、无权限、会话冲突、上游超时 / 限流和供应商错误，避免把原始上游异常及密钥返回客户端。

SSE 事件约定：`run.started`、`text.delta`、`tool.started`、`tool.completed`、`run.completed`、`run.failed`。P3 先实现文字流，P4 增加工具事件。终态事件只发一次；流已开始后的错误使用流事件传递。供应商流式 tool arguments 先按 ID / index 聚合完整，再解析执行，禁止执行半截参数。

第一版断连后尽力取消上游并记录 Run 终态，不承诺 SSE 自动续传。前端凭 Run ID 查询最终状态，不能直接重发导致重复执行。若未来要求断线后继续执行和逐事件重放，再引入持久化事件与任务执行器。代理须配置流式转发、禁用缓冲和合理超时。

推荐业务后端作为调用入口，校验登录态后转交可信用户身份。本服务仍须验证服务凭据及身份声明；不直接信任请求体中的 app_id / user_id。跨用户访问测试是上线前必过项。浏览器直接访问时使用可验证的用户令牌，不能把千问密钥或内部服务共享密钥交给前端。CORS 不替代鉴权。

## 5. 实施顺序与验收目标

| 阶段 | 开发内容 | 完成标准 |
| --- | --- | --- |
| P1：最小对话链路 | 应用骨架、Settings、日志 / 错误、Provider、非流式 API、开发依赖 | uv 锁定安装成功；健康检查和 API 测试通过；Mock Provider 覆盖成功 / 超时 / 上游错误；实际 Ollama 对话通过；有密钥时另做一次千问验证 |
| P2：可持久化会话 | ORM、迁移、会话 / 消息 / Run、用户归属、上下文预算与幂等 | 重启后历史存在；多轮问题能引用上文；越权拒绝；并发冲突可预测；失败重试不重复写输入；生产数据库迁移验证通过 |
| P3：前端流式接入 | SSE、Run 查询、取消 / 错误、前端示例 | fetch 可以逐段显示；正常完成、上游故障与断连均有正确状态；JSON API 仍可使用；代理环境下不整段缓冲 |
| P4：Tool + Prompt + Skill | 注册表、参数校验、有界循环、模板与能力包、版本记录 | 本地与云端各验证一个支持工具的模型；模拟多工具、异常参数、未知工具、超时、最大轮数；同一 Skill 可切换供应商 |
| P5：上线准备 | 鉴权完善、数据库部署、Docker / CI、限流、审计、指标、集成文档 | 密钥仅后端持有；按用户隔离；核心流程回归通过；记录耗时 / 用量 / 错误；限流、超时、代理流式和数据备份恢复演练通过 |
| P6：Agent 演进 | 根据真实任务评估 LangGraph、任务队列、人工介入和长期记忆 | 先明确一个业务任务和状态流，再验收执行恢复、工具幂等、预算限制与可观察性 |

**第一版功能目标是 P1–P4；允许上线使用的版本还必须完成 P5。** P6 根据业务需求推进。阶段按验收结果推进，不把未经评估的工期作为承诺。

### 紧接着应执行的 P1 任务

1. 确定 `src/blog_server_agent` 包及资源打包方式，配置 uv 构建与 Ruff / pytest。
2. 添加 P1 运行和开发依赖，验证 Python 3.14 环境并更新锁文件。
3. 实现 Settings、`.env.example`、密钥忽略规则和 FastAPI 生命周期。
4. 定义自有消息、模型返回和 `LLMProvider`；实现公共兼容客户端及供应商差异配置。
5. 实现 ChatService、`/health/live`、`POST /api/v1/chat` 和错误映射。
6. 添加有意义的 Mock Provider / HTTP 测试，覆盖验证失败、超时与错误映射。
7. 本地 Ollama 验证；有千问凭据时完成真实云端冒烟测试，记录支持能力；补充实际启动与调用命令。

P1 暂不保存历史，API 文档必须说明它是单轮验证接口；持久化在 P2 交付。若暂时没有云端凭据，分别标记“适配代码已验证”和“真实千问联调待完成”，不宣称已实现双端实测。

## 6. 质量与上线约束

- SDK 重试与应用重试只在一处统筹；首期显式控制次数与总时限，避免多层重试叠加。已发出文本或执行过有副作用工具时不能自动重放整轮。
- 记录 request_id / run_id、模型、Prompt / Skill 版本、耗时、工具状态及供应商实际返回的 usage。默认不记录完整对话、密钥和工具敏感结果。
- 开发可用 SQLite；生产若用 PostgreSQL，必须对目标数据库实际执行迁移与集成测试，不能从 SQLite 测试推定兼容。
- 以每会话单活跃 Run 降低初期复杂度，同时设请求长度、上下文、输出、工具轮数和整体时限。
- CI 默认使用模拟模型，不在每次测试付费调用；真实供应商冒烟测试显式运行。评测用固定小样本检查对话、结构化输出及工具选择，不能只断言模型返回非空。
- 部署前确定调用链路和可信身份来源、数据库方案、本地模型及硬件、千问地域与模型权限；这些信息不妨碍先推进 P1 骨架与模拟测试。

## 7. 官方依据

以下链接用于实现时核对接口细节；能力、模型名与地域信息应以届时实际控制台和官方文档为准。

- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)：本地 URL、占位 key、流式与工具能力及兼容范围。
- [千问 OpenAI Chat 接口兼容](https://help.aliyun.com/zh/model-studio/compatibility-of-openai-with-dashscope)：配置切换、业务空间域名、地域与密钥匹配。
- [千问 Function Calling](https://docs.modelstudio.console.alibabacloud.com/en/model-studio/qwen-function-calling)：模型返回调用指令，应用执行工具并回传结果；不同模型与思考模式有参数差异。
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)：共享客户端与连接资源的初始化及释放。
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)：环境变量与配置校验。
- [SQLAlchemy asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)：异步会话及并发使用边界；落地时以所选版本文档为准。
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)：状态工作流、持久化执行、人工介入及与 LangChain 的关系。
