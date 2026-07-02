# Infinite-Canvas 开发规则 (agents.md)

> 本文档是 AI 辅助开发时的唯一事实来源 (SSoT)。所有代码变更、架构决策、工作流程均需遵循以下规则。

---

## 一、项目概览

| 项目 | 说明 |
|------|------|
| 项目名称 | Infinite-Canvas（无限画布） |
| 项目类型 | 本地 AI 图像/视频生成画布应用 |
| 当前版本 | 2026.06.30（见 [VERSION](./VERSION)） |
| 授权协议 | 禁止商业用途，二次开发须保持开源并注明来源（见 [LICENSE](./LICENSE)） |
| 后端技术栈 | Python 3.10+ / FastAPI / Uvicorn |
| 前端技术栈 | 原生 HTML + CSS + JavaScript（无构建工具） |
| 核心依赖 | fastapi, uvicorn, requests, pydantic, python-multipart, httpx, pillow（见 [requirements.txt](./requirements.txt)） |
| 主要 AI 平台 | OpenAI 兼容 API / ComfyUI / ModelScope / RunningHub / 火山引擎 / 即梦 CLI / Codex CLI |

---

## 二、项目架构

### 2.1 目录结构

```
Infinite-Canvas/
├── main.py                     # 后端主程序（单文件 FastAPI 应用）
├── requirements.txt            # Python 依赖
├── VERSION                     # 版本号
├── LICENSE                     # 授权协议
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── README.md                   # 项目说明
├── 新手运行与使用教程.md         # 详细使用教程
├── Dockerfile                  # Docker 构建文件
├── docker-compose.yml          # Docker 编排
├── docker-compose.deploy.yml   # 服务器部署编排
├── run.bat / mac-启动服务.sh   # 各平台启动脚本
├── 安装依赖.bat / mac-安装依赖.sh  # 各平台依赖安装脚本
├── CLI/                        # 第三方 CLI 工具安装脚本
├── tools/                      # 配套工具
│   ├── chrome-local-asset-importer/   # Chrome 素材采集插件
│   └── photoshop-asset-connector/     # Photoshop 插件
├── workflows/                  # ComfyUI 工作流 JSON 文件
├── data/                       # 运行时数据（不提交到 Git）
│   ├── users.json              # 用户数据
│   ├── projects.json           # 项目数据
│   ├── asset_library.json      # 素材库
│   ├── prompt_libraries.json   # 提示词库
│   └── users/<user_id>/        # 各用户独立配置
├── assets/                     # 本地素材（不提交）
├── output/                     # 生成输出（不提交）
└── static/                     # 前端静态资源
    ├── *.html                  # 页面（index, canvas, smart-canvas, canvas-list 等）
    ├── css/                    # 样式
    ├── js/                     # 脚本
    │   └── i18n/               # 国际化文件
    ├── images/                 # 图片资源
    ├── vendor/                 # 第三方库（tailwindcss, lucide, three.js, 字体）
    ├── runninghub/             # RunningHub 平台配置
    └── system-prompts/         # 预设提示词模板
```

### 2.2 后端架构

后端为单文件 FastAPI 应用 `main.py`，核心模块包括：

| 模块 | 说明 | 大致行号 |
|------|------|----------|
| 启动与基础配置 | CORS、WebSocket 连接管理、静默日志 | 1-200 |
| 环境变量管理 | `.env` 加载、模型列表、API Provider 配置 | 440-1400 |
| 版本与更新 | 版本检查、更新通知、HTML 版本同步 | 1409-1600 |
| APP 信息接口 | `/api/app-info`、连通性探测 | 1690-1790 |
| 更新系统 | 在线更新、回滚、备份 | 1835-2320 |
| 即梦/视频相关 | Jimeng 状态、积分、登录、媒体查询 | 4486-10700 |
| 媒体/上传 | 图片预览、下载、上传、本地素材管理 | 5091-10180 |
| RunningHub | 工作流提交、查询、资产管理 | 10187-10500 |
| Codex / Jimeng CLI | CLI 工具状态、帮助、登录 | 10506-10708 |
| 配置与模型 | Provider CRUD、模型获取、连接测试 | 10708-11480 |
| 图像生成 | 在线图像、画布图像任务、参数获取 | 11484-12186 |
| 视频生成 | 画布视频任务 | 12186-12637 |
| LLM 对话 | 对话、会话管理 | 12637-12750 |
| 画布管理 | 画布 CRUD、智能画布、素材、工作流 | 12750-13200 |
| 资产/提示词库 | 素材库、提示词库管理 | 13200- |

> **注意**：`main.py` 超过 13000 行，是一个巨大的单文件。修改时需谨慎，避免破坏其他功能。

### 2.3 前端架构

前端为纯静态页面，无构建工具：

- **页面**：13 个 HTML 页面，对应不同功能模块
- **样式**：独立 CSS 文件 + Tailwind CSS CDN
- **脚本**：原生 JS，按页面拆分
- **国际化**：`js/i18n/` 目录下各模块独立的 i18n 文件
- **第三方库**：通过 `static/vendor/` 直接引入（无 npm）

---

## 三、代码规范

### 3.1 通用规则

1. **函数级注释**：所有函数必须添加函数级注释（中文），说明功能、参数、返回值
2. **生产代码无调试语句**：禁止在提交的代码中留下 `console.log`、`print` 等调试语句
3. **环境变量**：不得硬编码敏感配置，必须通过 `os.environ.get()` 从环境变量读取，模板写入 `.env.example`
4. **API 入参验证**：新增 API 必须使用 Pydantic 模型进行入参验证
5. **数据库查询**：如涉及 SQL 查询，必须使用参数化查询，禁止字符串拼接

### 3.2 Python 后端规范

- 使用 FastAPI 路由装饰器：`@app.get`、`@app.post`、`@app.put`、`@app.patch`、`@app.delete`
- 路由路径统一以 `/api/` 开头
- 使用 Pydantic `BaseModel` 定义请求/响应模型
- 异常处理使用 `@app.exception_handler` 统一处理
- WebSocket 使用 `ConnectionManager` 类管理连接
- 文件操作使用 `pathlib.Path` 或 `os.path`，注意跨平台兼容性
- 异步操作优先使用 `async/await` + `httpx`，而非同步 `requests`

### 3.3 前端规范

- 使用原生 JavaScript，不引入框架
- DOM 操作使用原生 API，优先 `querySelector` / `querySelectorAll`
- 样式优先使用 Tailwind CSS 工具类，自定义样式写入对应 CSS 文件
- 国际化通过 `i18n.js` 系统管理，新增文案需同步更新各语言文件
- 前端与后端通信使用 `fetch` API

### 3.4 命名约定

| 类型 | 规则 | 示例 |
|------|------|------|
| Python 文件/模块 | 蛇形命名 | `main.py` |
| Python 函数 | 蛇形命名 | `load_api_providers()` |
| Python 类 | 大驼峰 | `ConnectionManager` |
| Python 常量 | 全大写蛇形 | `REQUEST_TIMEOUT` |
| JS 变量/函数 | 小驼峰 | `fetchProviders()` |
| JS 类 | 大驼峰 | `CanvasManager` |
| CSS 类 | kebab-case | `.canvas-container` |
| API 路径 | kebab-case | `/api/canvas-image-tasks` |
| 环境变量 | 全大写蛇形 | `COMFLY_API_KEY` |

---

## 四、工作流规则 (VibeCoding)

### 4.1 RIPER-10 协议

所有开发任务遵循 RIPER-10 标准作业流：

| 阶段 | 名称 | 说明 |
|------|------|------|
| Phase 0 | Structure First | PDM 输出需求结构化解析 |
| Phase 1 | P.A.C.E. 智能分流 | PM 选择 Path A/B/C |
| R1 | Research | 全知感知，扫描项目，分析差距 |
| I | Innovate | 虚拟专家会议，架构决策 |
| P | Plan | 任务拆解，WBS，用户确认 |
| E | Execute | 高并发执行，自测 |
| R2 | Review | 完整性校验，经验沉淀，交付 |

### 4.2 P.A.C.E. 路径选择

- **Path A - 闪电模式**：简单 Bug 修复、单文件修改、即时问答。跳过 I 和 P 阶段。
- **Path B - 协作模式**：新功能开发、多模块重构、复杂需求。完整 RIPER 循环。
- **Path C - 系统模式**：从 0 到 1 建项目、全系统架构设计。深度迭代，高频确认。

### 4.3 六条工作流铁律

1. **不得在 E 阶段修改 design.md**（设计已锁定）
2. **plan.md 中未完成的任务不能标记为 DONE**
3. **.knowledge/ 目录下的文件不可删除，只能追加内容**
4. **conventions.md 文件的变更需经过寸止确认**
5. **每次 commit 必须关联 plan.md 中的任务编号（Path B+）**
6. **修复 bug 必须编写回归测试（Path B+）**

### 4.4 Git 提交规范

**Commit Message 格式**：
```
type(scope): description [T-XXX]
```

- **type**：feat / fix / refactor / docs / style / test / chore
- **scope**：backend / frontend / canvas / api / docker 等
- **T-XXX**：对应任务编号

**合并规则**：
- Path B 类型任务：使用 **squash merge** 合并到主分支
- Path C+ 类型任务：按功能分 commit，保留完整历史

---

## 五、Torvalds' Checklist（写代码前自检）

每次写代码前，必须在内心过一遍这份清单：

| 检查项 | 问题 |
|--------|------|
| **Taste** | 代码逻辑是不是像面条？能不能优化数据结构？ |
| **Stable** | 我有没有破坏原来的接口？(Don't break userspace) |
| **Reality** | 我是在写代码，还是在写科幻小说？(API 存在吗？) |
| **Tests** | 我该怎么测这段代码？ |

**信条**：
- "Show me the code" — 空谈误国，设计讨论必须落地为可执行代码
- "Good Taste" — 追求极简，数据结构优于算法
- "Don't break userspace" — 接口兼容性是铁律
- "Given enough eyeballs" — 每一个 Bug 都是因为视角不够

---

## 六、虚拟专家团 (Hexagon Roles)

AI 在内部动态切换以下"思维帽子"：

| 角色 | 名称 | 职责 |
|------|------|------|
| 🎩 PM | 项目总控 | P.A.C.E. 决策、用户交互、任务编排 |
| 🎩 AR | 架构师 | 系统设计，信条：烂程序员关心代码，好程序员关心数据结构 |
| 🎩 PDM | 产品经理 | 需求结构化解析 |
| 🎩 LD | 开发领队 | 代码实现，信条：代码必须是干净的 |
| 🎩 QA | 测试专家 | 破坏性思维和 E2E 测试，信条：未测试的代码 = 垃圾 |
| 🎩 DW | 文档专家 | 维护唯一的真理来源 (SSoT) |

---

## 七、关键文件索引

| 文件 | 作用 | 修改注意事项 |
|------|------|-------------|
| [main.py](./main.py) | 后端主程序 | 文件巨大（13000+ 行），修改需确认影响范围 |
| [.env.example](./.env.example) | 环境变量模板 | 新增环境变量必须同步更新此文件 |
| [requirements.txt](./requirements.txt) | Python 依赖 | 新增依赖必须在此声明 |
| [.gitignore](./.gitignore) | Git 忽略规则 | data/、assets/、output/、.env 不可提交 |
| [VERSION](./VERSION) | 版本号 | 每次发布更新此文件（YYYY.MM.DD） |
| [static/update-notes.json](./static/update-notes.json) | 更新说明 | 版本更新时同步更新 |
| [README.md](./README.md) | 项目说明 | 重大功能更新时同步更新 |
| [UPDATE.md](./UPDATE.md) | 更新日志 | 每次迭代更新 |

---

## 八、数据与配置

### 8.1 运行时数据目录（不提交）

| 目录/文件 | 内容 |
|-----------|------|
| `data/` | 用户数据、项目数据、素材库、提示词库、各用户配置 |
| `assets/` | 本地素材文件 |
| `output/` | AI 生成的图片/视频输出 |
| `.env` | 环境变量（敏感信息） |
| `data/history.json` | 历史记录（存于 data/ 下以确保 Docker 卷持久化） |
| `global_config.json` | 全局配置 |

### 8.2 环境变量

详见 [.env.example](./.env.example)，主要分类：
- AI 服务配置（Comfly、ModelScope）
- 模型配置（默认模型、自定义模型列表）
- ComfyUI 配置（多实例支持）
- 公网访问配置
- 请求超时与轮询
- 输入限制
- CLI 工具配置
- 临时素材上传配置

---

## 九、文档维护规则

1. **主要维护**：`README.md` 和 `UPDATE.md`，尽量减少新建文档文件
2. **文档格式**：使用 Markdown 格式
3. **agents.md**：本文档是 AI 开发规则的 SSoT，如有变更需在此更新
4. **知识沉淀**：经验教训存入 `.knowledge/` 目录（仅追加，不可删除）

---

*最后更新：2026-07-02*
