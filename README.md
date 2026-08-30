# MySelfAgent - LangChain Agent 学习项目

> **版本**: v1.5.0
> **状态**: 第一版，未经人工验证，后续功能增量添加，README 同步更新
> **最后更新**: 2026-08-29

---

## 项目简介

基于 LangChain 的 Agent 系统学习项目，采用 **TDD（测试驱动开发）** 方式构建。

四个核心模块：**LLM**（决策者）/ **工具系统**（执行者）/ **记忆系统**（持久化）/ **规划模块**（目标分解）。

### 工作流程

```
目标输入 -> 规划 -> LLM决策工具 -> 执行 -> 结果存入记忆 -> LLM评估 -> ... -> 任务完成
```

### 架构图

```
                    +---------------------------+
                    |         Agent 核心         |
                    |  (规划->决策->执行->评估    |
                    |   ->存记忆->再决策 循环)    |
                    +---+-------+-------+-------+
                        |       |       |
               +--------+--+ +--+---+ +-+----------+
               | LLM 规划器 | | 工具 | | 上下文管理器 |
               | (分解目标  | | JSON | | (token追踪  |
               |  评估结果  | |Schema| |  自动压缩   |
               |  动态调整) | +--+--- |  输出截断)  |
               +--------+--+    |     +------------+
                        |   +---+----+
                    +---+---+---+  +--+--------+
                    |python_exec|  |BufferMemory|
                    |file_io    |  |(JSON持久化)|
                    |search     |  +------------+
                    |datetime   |
                    +-----------+
```

---

## 快速开始

### 1. 环境准备

```bash
git clone https://github.com/tripodxu/myselfagent.git
cd myselfagent
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. 配置

复制 `.env.example` 为 `.env` 并修改。需要兼容 OpenAI responses 格式的本地 LLM API。

默认：`http://127.0.0.1:8788/v1/responses`，模型 `oxx`

### 3. 运行

```bash
# 单次任务
python main.py "查询今天的日期"

# 交互模式
python main.py --interactive

# 调试模式（实时看到LLM流式输出、工具调用、时间戳）
python main.py --interactive --debug
```

### 4. 测试

```bash
pytest -v                    # 全部测试
pytest --cov=src             # 覆盖率
pytest tests/test_llm.py     # 特定模块
python examples/full_test.py # 完整功能测试（10项）
```

---

## 项目结构

```
myselfagent/
+-- main.py                    # 主入口
+-- config.py                  # 配置文件
+-- requirements.txt           # 依赖包
+-- src/
|   +-- llm.py                 # LLM模块（流式输出、重试退避、推理控制）
|   +-- agent.py               # Agent核心（分层消息、安全审查、评估驱动循环）
|   +-- tools/
|   |   +-- base.py            # 工具基类 + 注册表（JSON Schema）
|   |   +-- python_exec.py     # 安全执行Python代码
|   |   +-- file_io.py         # 文件读写列目录
|   |   +-- search.py          # 文本/文件搜索（正则）
|   |   +-- datetime_tool.py   # 日期时间（支持中文相对日期）
|   +-- memory/
|   |   +-- base.py            # 记忆基类
|   |   +-- buffer.py          # 缓冲记忆（JSON持久化）
|   |   +-- context_manager.py # 上下文管理器
|   +-- planner/
|       +-- llm_planner.py     # LLM规划器（分解/评估/动态调整）
|       +-- simple.py          # 简单规划器（备用）
+-- tests/                     # 104个测试，全部通过
+-- examples/
    +-- demo.py
    +-- full_test.py           # 10项完整功能测试
```

---

## 模块说明

### LLM 模块 (src/llm.py)

- **流式输出**：SSE 实时解析，调试模式下逐字打印
- **指数退避重试**：1s -> 2s -> 4s
- **推理深度控制**：简单任务 low，复杂任务 high，自动判断
- **降级机制**：流式失败自动切换同步

### 工具系统 (src/tools/)

每个工具实现 `parameters_schema()` 返回 JSON Schema，LLM 精确选择工具：

- **python_exec**：安全执行代码，拦截危险导入（subprocess、socket 等）
- **file_io**：读写列目录，路径白名单安全检查
- **search**：正则搜索文本或文件
- **datetime**：当前日期时间、相对日期（+N、明天等）

### 记忆系统 (src/memory/)

- **BufferMemory**：消息列表，max_size 裁剪，JSON 文件持久化
- **ContextManager**：token 追踪、自动压缩旧消息、工具输出截断（500字符）、系统消息始终保留

### 规划模块 (src/planner/)

- **LLMPlanner**：LLM 将目标分解为 2-5 个步骤（合并相关操作），每步执行后评估结果（continue/stop/replan），支持动态调整
- **SimplePlanner**：目标作为单一任务，备用

### Agent 核心 (src/agent.py)

**评估驱动循环**（v1.4.0 改进）：

```
阶段1: LLM 分解目标 -> ["步骤1", "步骤2"]（限制2-5步，合并相关操作）
阶段2: 循环 {
    LLM 决策工具（分层消息：系统规则/用户目标/历史结果）
    安全审查（拦截危险模式）
    执行工具
    LLM 评估结果 -> continue / stop / replan  <-- 唯一的停止条件
}
阶段3: 选择最佳结果返回
```

**v1.5.0 关键改进**：
- 当 `evaluate=continue` + 步骤耗尽时，自动 replan 继续执行
- Planner/决策/评估 prompt 全面优化，要求生成实际代码而非计划文本

**v1.4.0 关键改进**：
- 移除 `has_answer()` 作为提前终止条件（之前读到文件内容就停了）
- 停止决策完全由 LLM `evaluate_result` 控制
- Planner 限制 2-5 步，鼓励合并相关操作
- 避免过度分解（之前9步，现在2-5步）

### 调试模式

```
[20:52:42.265] [GOAL] Goal: 分析文件
[20:52:42.265] [CONFIG] Reasoning effort: medium
[20:52:42.265] [PLAN] Plan created: 3 steps
[20:52:42.938] [ITER] Iter 1: Step 1
[20:52:42.938] [DECIDE] Deciding...
[20:52:42.940] [MSG] [DEVELOPER] You are an AI agent...
[20:52:42.941] [MSG] [USER] Goal: 分析文件
[20:52:42.942] [API_REQ] Full prompt sent to LLM
{"tool":"python_exec","params":{"code":"..."}}    <- 流式实时输出
[20:52:43.100] [API_RES] LLM response complete (85 chars)
[20:52:43.100] [SAFETY] Safety: ok
[20:52:43.101] [EXEC] Executing...
[20:52:43.150] [RESULT] Result: {"success": true, "output": "..."}
[20:52:43.151] [EVAL] Eval: stop - goal achieved
[20:52:43.152] [CTX] Context: 450 tokens, 15% used
[20:52:43.152] [DONE] Done: 0.89s, 1 iters
```

---

## 测试统计

| 模块 | 测试数 | 覆盖内容 |
|------|--------|----------|
| LLM | 6 | 初始化、调用、重试、超时、流式 |
| 工具基类 | 10 | 注册表、Schema、获取/列表 |
| Python执行 | 8 | 执行、错误、安全限制 |
| 文件IO | 8 | 读写、列表、权限 |
| 搜索 | 11 | 文本、文件、正则、过滤 |
| 记忆基类 | 7 | 添加、获取、清除、搜索、摘要 |
| 缓冲记忆 | 9 | 存储、检索、持久化、max_size |
| 上下文管理 | 11 | token、压缩、截断、统计 |
| LLM规划器 | 15 | 创建、评估、动态调整、降级 |
| 简单规划器 | 9 | 创建、更新、完成、进度 |
| Agent | 10 | 初始化、循环、错误、记忆、安全 |

**总计：104个测试，全部通过**

---

## 更新日志

### v1.5.0 - 智能 Replan + 输出验证 (2026-08-30)

**核心修复**：
- Agent 循环：当 `evaluate=continue` 但计划步骤耗尽时，自动触发 replan（让 LLM 生成新步骤）
- Planner prompt 优化：要求生成完整可运行代码，而非计划文本或占位符
- 评估 prompt 优化：严格区分"计划描述"和"实际实现"，只有真正完成才 stop
- 决策 prompt 优化：明确要求写完整实现，不写伪代码

**修复的问题**：
- Agent 读取计划文件后输出计划文本而非实现 -> prompt 要求生成完整代码
- 评估说"continue"但 Agent 直接退出 -> 自动 replan 继续执行
- LLM 把计划当成内容展示 -> 评估 prompt 区分计划和实现

### v1.4.0 - 评估驱动循环 (2026-08-29)

**核心修复**：
- 移除 `has_answer()` 作为提前终止条件，避免中间步骤（如读文件）触发停止
- 停止决策完全由 LLM `evaluate_result` 控制
- Planner 限制 2-5 步，鼓励合并相关操作到一个 python_exec 调用
- `_build_messages` 增加 "Combine related operations" 规则

**修复的问题**：
- Agent 读取文件后立即停止（1轮迭代） -> 现在会继续执行直到 LLM 评估认为目标达成
- Planner 过度分解（9步） -> 现在限制 2-5 步
- LLM 效率低（每轮只做一个操作） -> prompt 鼓励合并操作
- Mock 测试缺少 `use_stream` 属性 -> 已修复

### v1.3.0 - 上下文管理 (2026-08-29)

- `ContextManager`：token 追踪、自动压缩、工具输出截断
- 系统消息始终保留在上下文窗口
- 预算感知的上下文检索
- 调试模式显示上下文使用率

### v1.2.0 - Codex 启发的优化 (2026-08-29)

- JSON Schema 工具定义（`parameters_schema()`）
- 分层消息系统（developer / user / assistant）
- 安全审查层（执行前拦截危险模式）
- 推理深度控制（自动 low/medium/high）

### v1.1.0 - LLM 规划器 (2026-08-29)

- `LLMPlanner`：LLM 分解目标、评估结果、动态 replan
- Agent 循环：规划 -> 决策 -> 执行 -> 评估（continue/stop/replan）
- 新增15个规划器测试

### v1.0.1 - Bug 修复 (2026-08-29)

修复6个核心问题：
1. **编码崩溃**：`sys.stdout.reconfigure()` 替代替换 stream
2. **Agent 不停**：`has_answer()` 检测答案提前终止
3. **无反馈**：之前结果传入 LLM
4. **假规划**：目标作为单一任务，非固定5步
5. **无退避**：指数重试（1s, 2s, 4s）
6. **选错答案**：`select_best_result()` 选最有内容的结果

### v1.0.0 - 最小可用版本 (2026-08-29)

- 项目结构、TDD 方式
- LLM、工具、记忆、规划、Agent 核心
- 78个测试全部通过

---

## 后续计划

1. 向量记忆（长期存储）
2. 网络搜索集成
3. 多 Agent 协作
4. Web UI
5. 更多工具（数据库、API 调用）

---

> **注意**：本项目为学习项目，代码未经人工验证，仅供参考学习。后续功能增量添加，README 同步更新。
