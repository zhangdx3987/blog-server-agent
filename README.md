# blog-server-agent

面向其他业务项目和前端页面的 Python AI 后端服务，计划统一管理模型调用、会话、Prompt、Skill 与 Tool，并逐步支持 Agent 执行逻辑。

## 当前状态

截至 2026-11-11，仓库处于初始化阶段：

- 使用 `uv`，已有 `pyproject.toml`、`uv.lock` 和本地虚拟环境。
- Python 配置为 `>=3.14`，`.python-version` 为 `3.14`。
- `main.py` 目前仅输出 Hello；尚无 HTTP 服务、模型适配、数据库、工具或测试。
- 下文均为待实现设计；目前不能按这些接口调用服务。

## 推荐方向

采用 **FastAPI + 异步模型适配层 + 应用服务层 + 数据持久化** 的模块化单体结构。开发连接本地 Ollama，上线连接阿里云百炼千问，由配置切换供应商。

第一版通过 OpenAI 兼容的 Chat Completions 协议连接两端，在自有模型接口中隔离供应商参数。会话历史保存在本服务中。优先完成普通对话、历史、流式输出和安全的工具循环，再按需求增加复杂 Agent 编排。

完整的目录规划、依赖选择、接口约定和逐阶段验收标准见 [开发计划](docs/development-plan.md)。

## 下一步目标

第一阶段交付可验证的最小链路：

```text
调用方 → POST /api/v1/chat → ChatService → LLMProvider → Ollama / 千问
```

包含配置加载、健康检查、非流式对话、超时与错误映射、可替换的模型客户端和自动化验证。随后加入持久化会话与 SSE，再完成 Tool、Prompt 和 Skill。

当前可用的命令仅为初始化入口：

```bash
uv sync
uv run main.py
```

服务启动命令与 `.env.example` 将在第一阶段实现后补充。
