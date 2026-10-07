# SNhelper Web 控制面板工作记录

## 已完成

- 建立 `web/` 前端工程：Vite + React + TypeScript + Tailwind CSS。
- 完成 Dashboard、Chat、Quick Capture、Task Board、Search、Settings 六个主要页面。
- 使用 React Router 管理页面路由，使用 Zustand 管理项目上下文与主题。
- API 层支持 `VITE_API_URL`、Mock 模式、REST 请求和 `/chat` 流式响应。
- Chat 支持 Markdown、GFM 和代码高亮，并展示 Agent 路由标签。
- Dashboard 支持健康状态、Agent 列表、最近对话、最近任务和项目切换。
- Task Board 支持完成切换、15 分钟粒度添加任务。
- Search 支持记忆搜索、标签过滤和匹配度展示。
- Settings 支持 API 地址、API Key、深浅色主题和长期记忆入口。
- 已修复 Chat 页面因 `useEffect` 隐式返回值导致的白屏问题。
- 已验证 `npm run build` 构建通过。
- P0 联调基础：API 请求增加 20 秒超时、GET 重试、可取消请求和统一 `ApiError`。
- Chat 流式兼容 SSE、JSON、纯文本响应，支持停止生成；前端用 `requestAnimationFrame` 合并增量，减少逐 token 重渲染。
- 灵感速记支持最近记录回顾、编辑和删除。
- 执行清单支持新增、完成切换、编辑和删除。
- 知识检索结果支持编辑和删除。
- 项目支持从工作区选择器新增，并在设置页新增、编辑和删除。
- API Key 连接配置已接入所有请求和对话流。
- 对话历史按项目持久化到 `snhelper-conversations-v1`，支持新建、切换、重命名、删除和清空。
- 对话发送时自动带上最近 10 条消息作为上下文，Mock/真实流式输出都支持停止。
- Mock 速记与知识记忆持久化到浏览器 localStorage，刷新后仍可回顾、编辑和删除。
- 灵感速记支持选择 Archivist、Enforcer、Strategist、Simulator 进行 Agent 辅助标签建议，并可逐个采纳。
- 桌面端左侧导航固定为独立 `100vh` 滚动区域，不随主内容滚动。
- 新增 `snhelper/web_api.py` FastAPI 后端：健康检查、项目/任务/速记/记忆 CRUD、搜索、Agent 标签建议、JSON 对话和 SSE 流式对话。
- 后端项目、任务、速记和长期记忆统一持久化到 SQLite；速记保存时同步写入长期记忆，编辑和删除保持一致。
- FastAPI 支持 `SNHELPER_API_KEY` Bearer Token 鉴权和前端开发端口 CORS；可用 Uvicorn 独立启动。
- 设置页新增调用模式：Mock、FastAPI REST、FastAPI SSE，运行时写入 `snhelper-call-mode`，不需要重新构建前端即可切换。
- 新增 `tests/test_web_api.py`，覆盖鉴权、健康检查、项目/任务/速记/搜索、JSON 对话和 SSE 对话；真实 Uvicorn 端口联调已通过。
- 外部模型连接配置已独立于 FastAPI 配置：设置页支持 OpenAI 兼容的模型地址、模型 Key、模型名和连接测试；FastAPI 后端代理 `/provider/test` 与 `/chat`，避免浏览器直接暴露模型 Key。
- 模型服务地址、Key 和模型名称在输入时即时持久化，切换页面后不会恢复为默认的 `gpt-4o-mini`。
- 系统设置新增长期记忆管理：按需加载最近记忆，支持刷新、编辑标签/内容和删除，并复用 Search 的记忆 API。
- 总览已从静态预览改为可用工作台：最近对话读取持久化会话并可直接打开，今日任务支持直接勾选并同步 API，专注时间支持持久化启动/暂停计时并结合完成任务时长，指标卡和快捷入口均可操作。
- 总览和执行清单日期改为本地动态日期，不再显示固定示例日期。
- 灵感速记的 Agent 辅助分类会显示请求错误，成功后自动应用建议标签并标出分类 Agent。
- 对话中枢发送前自动检索相关灵感速记；Mock、FastAPI REST、FastAPI SSE 和外部模型代理都会接收记忆上下文，并在回答中标明引用的速记。
- Mock 检索支持中文二字片段和英文关键词匹配，能够处理自然语言提问，不再要求整句完全匹配速记内容。

## 当前约定

- 默认使用 Mock 数据；可在设置页切换调用模式，也可在 `.env` 中使用 `VITE_CALL_MODE=fastapi-rest` 或 `VITE_CALL_MODE=fastapi-sse` 设置默认模式。
- FastAPI 默认启动命令：`uvicorn snhelper.web_api:app --reload --host 127.0.0.1 --port 8000`。
- 后端 API Key 通过 `SNHELPER_API_KEY` 配置；为空时关闭鉴权，前端 API Key 字段为空则不发送鉴权头。
- “FastAPI 地址”必须填写 SNhelper 后端地址；外部供应商地址填写在“外部模型服务”，例如 `https://api.openai.com/v1` 或 `https://api.deepseek.com/v1`，不要用供应商地址替换 FastAPI 地址。
- API 地址保存在 `localStorage` 的 `snhelper-api-url`。
- API Key 保存在 `localStorage` 的 `snhelper-api-key`，请求时通过 `Authorization: Bearer <api_key>` 发送。
- 左下角 Agent 状态是系统在线状态摘要；主理人是当前本地工作实例身份，不代表登录账号体系。

## 未来迭代计划

### P0：后端联调与可靠性（已完成基础版）

- 对齐 LangGraph 生产服务的真实响应字段、SSE 事件字段和错误码。
- 将 SQLite WebStore 替换为生产数据库或现有 LangGraph 持久化层，并增加并发写入策略。
- 将当前页面级错误提示统一成可恢复的 Toast/错误面板。
- 增加登录或本地访问令牌轮换，避免 API Key 长期保存在浏览器 localStorage。

### P1：认知工作流增强

- Chat 支持 SSE 事件级展示：路由、检索、工具调用、最终回答。
- 支持从对话直接生成任务、项目和知识记忆。
- 增加长期记忆详情、编辑、软删除和恢复。
- 增加项目创建、归档、颜色和项目级 Agent 配置。
- 支持对话历史持久化、搜索和重新打开。

### P2：运维与体验

- 增加 Agent 运行耗时、调用次数、错误率和成本统计。
- 增加离线状态、断线重连和移动端 PWA 能力。
- 增加可配置快捷键、通知中心和未读消息状态。
- 添加组件测试、API mock 测试、路由 smoke test 和移动端视觉回归。
- 按路由拆分代码包，优化 Markdown/代码高亮带来的首屏体积。

## 本次修复

- 修复对话页历史对话侧栏被超长标题撑出边界的问题：为侧栏、历史列表、条目标题和操作区增加 `min-width`/`max-width`/`overflow` 约束。
- 历史列表增加独立的纵向滚动区域，标题和日期信息在条目内使用省略号展示，长文本不会改变主界面宽度。
- 验证：`npm run build` 通过，`python -m pytest -q` 通过（5 passed）；浏览器检查侧栏与历史列表 `scrollWidth` 均未超过 `clientWidth`。
