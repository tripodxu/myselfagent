# MySelfAgent - LangChain Agent 学习项目

> **版本**: v1.2.0
> **状态**: 第一版，未经人工验证，后续功能增量添加，README文档同步更新
> **最后更新**: 2026-08-29

---

## 项目简介

基于 LangChain 的 Agent 系统学习项目，采用 **TDD（测试驱动开发）** 方式构建。

Agent 由四个核心模块组成：LLM（决策者）、工具系统（执行者）、记忆系统（避免失忆）、规划模块（拆分大目标为小步骤）。

### 工作流程

`
目标输入 -> 规划 -> LLM决策 -> 工具执行 -> 结果存入记忆 -> LLM再决策 -> ... -> 任务完成
`

核心循环由 LLM 驱动：每轮迭代中，LLM 根据目标和之前的执行结果，选择合适的工具执行，直到检测到任务完成。

---

## 快速开始

### 1. 环境准备

`ash
git clone https://github.com/tripodxu/myselfagent.git
cd myselfagent
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
pip install -r requirements.txt
`

### 2. 配置

复制 .env.example 为 .env 并修改配置。需要一个兼容 OpenAI 格式的本地 LLM API。

### 3. 运行

`ash
# 单次执行
python main.py "查询今天的日期"

# 交互模式
python main.py --interactive

# 调试模式（可观测每一步的API交互）
python main.py --interactive --debug
`

### 4. 测试

`ash
pytest -v                    # 运行全部测试
pytest --cov=src             # 查看覆盖率
pytest tests/test_llm.py     # 运行特定模块测试
`

---

## 项目结构

`
myselfagent/
├── main.py                 # 主入口
├── config.py              # 配置文件
├── requirements.txt        # 依赖包
├── .env.example           # 环境变量示例
├── pytest.ini             # pytest配置
├── src/
│   ├── __init__.py
│   ├── llm.py             # LLM模块（连接本地API）
│   ├── agent.py           # Agent核心（决策循环）
│   ├── tools/             # 工具系统
│   │   ├── base.py        # 工具基类 + 注册表
│   │   ├── python_exec.py # Python代码执行
│   │   ├── file_io.py     # 文件读写
│   │   ├── search.py      # 搜索工具
│   │   └── datetime_tool.py # 日期时间工具
│   ├── memory/            # 记忆系统
│   │   ├── base.py        # 记忆基类
│   │   └── buffer.py      # 缓冲记忆（带JSON持久化）
│   └── planner/           # 规划模块
│       └── simple.py      # 简单规划器
├── tests/                 # 78个测试，全部通过
└── examples/
    └── demo.py            # 演示脚本
`

---

## 模块说明

### LLM 模块 (src/llm.py)
自定义 LLM 类，连接本地 API（兼容 OpenAI responses 格式）。支持自动重试（指数退避）和超时处理。

### 工具系统 (src/tools/)
- **Python执行工具**: 安全执行Python代码，限制危险模块导入（subprocess、shutil等）
- **文件IO工具**: 文件读写操作，带路径安全检查
- **搜索工具**: 文本/文件搜索，支持正则表达式
- **日期时间工具**: 获取当前日期时间，支持中文相对日期（大后天、明天等）

### 记忆系统 (src/memory/)
缓冲记忆实现，支持自动持久化到JSON文件和上下文窗口管理。

### 规划模块 (src/planner/)
简单规划器，将目标作为单一任务跟踪，由 Agent 循环自主决定执行策略。

### Agent 核心 (src/agent.py)
整合所有模块的核心循环：
1. 接收目标
2. LLM 决策选择工具（带之前执行结果的上下文）
3. 执行工具
4. 检查是否获得答案 -> 有答案则提前结束
5. 将结果反馈给下一轮 LLM 决策
6. 重复2-5直到完成或达到最大迭代次数

---

## 调试模式

使用 --debug 或 -d 参数开启调试模式，可观测：
- 发送给 LLM 的完整提示词
- LLM 返回的原始响应
- 工具选择和参数
- 执行结果
- 每步耗时

所有日志带时间戳，便于定位瓶颈。

---

## 测试统计

| 模块 | 测试数 | 覆盖内容 |
|------|--------|----------|
| LLM模块 | 6 | 初始化、调用、重试、超时 |
| 工具基类 | 10 | 工具注册、获取、列表 |
| Python执行工具 | 8 | 执行、错误、安全限制 |
| 文件IO工具 | 8 | 读写、权限、路径安全 |
| 搜索工具 | 11 | 文本、文件、正则、过滤 |
| 记忆系统 | 16 | 存储、检索、持久化 |
| 规划模块 | 9 | 创建、更新、完成 |
| Agent核心 | 10 | 初始化、执行、错误处理 |

**总计: 93个测试，全部通过**

---

## 学习日志

### v1.1.0 - LLM Planner: 真正的规划引擎 (2026-08-29)

**核心改动**: Planner 从"被动进度记录器"升级为"LLM驱动的规划引擎"

**新增 `src/planner/llm_planner.py`**:
- `create_plan(goal)` - LLM 将目标分解为具体步骤
- `evaluate_result(step_result)` - LLM 评估每步结果，决定 continue/stop/replan
- `replan(new_steps)` - 动态调整计划，保留已完成步骤

**Agent 循环变为三次 LLM 调用**:
```
1. LLM 分解: goal -> ["step1", "step2", "step3"]
2. LLM 决策: step + tools + prior_results -> tool choice
3. LLM 评估: step_result + remaining_steps -> continue/stop/replan
```

**新增15个测试**: LLM Planner 全部通过

**测试总计**: 93个，全部通过

---

### v1.0.1 - Bug修复 (2026-08-29)

修复了 v1.0.0 中发现的6个核心问题：

**Bug 1: 编码崩溃 (main.py)**
- **现象**: ValueError: I/O operation on closed file
- **根因**: sys.stdout = io.TextIOWrapper(...) 替换了 stream 对象，旧对象被 GC 时关闭了底层 fd
- **修复**: 使用 sys.stdout.reconfigure(encoding='utf-8') 就地修改，不替换对象

**Bug 2: Agent 不停 (src/agent.py)**
- **现象**: 任务已在第1轮完成（输出34），但跑满5轮
- **根因**: 循环按 planner 固定步骤迭代，不检查任务是否已完成
- **修复**: 每轮执行后调用 has_answer() 检测，有答案立即终止

**Bug 3: 无反馈 (src/agent.py)**
- **现象**: LLM 不知道之前做了什么，重复执行
- **根因**: _make_decision() 不传入之前的执行结果
- **修复**: 将最近3轮的执行结果作为上下文传入 LLM 提示词

**Bug 4: 假规划 (src/planner/simple.py)**
- **现象**: 所有目标都分解为相同的5个通用步骤
- **根因**: _decompose_goal() 是硬编码的占位符
- **修复**: 将整个目标作为单一任务，由 Agent 循环自主驱动

**Bug 5: 无退避重试 (src/llm.py)**
- **现象**: LLM 过载时连续快速重试，全部超时
- **根因**: 重试间隔仅1秒
- **修复**: 指数退避（1s, 2s, 4s）

**Bug 6: 错误的答案 (src/agent.py)**
- **现象**: 最终结果是"文件已写入"而不是"34"
- **根因**: inal_result 选最后一个成功结果，而非包含实际答案的
- **修复**: select_best_result() 优先选择有 output 字段的结果

**其他改进**:
- python_exec 子进程强制 PYTHONIOENCODING=utf-8，修复中文乱码
- main.py 交互循环增加 ValueError 捕获，优雅退出
- 结果展示支持 bytes 类型自动解码

### v1.0.0 - 最小可用版本 (2026-08-29)

**完成内容：**
- [x] 项目结构搭建
- [x] LLM模块实现（连接本地 mimo API）
- [x] 工具系统实现（Python执行、文件IO、搜索、日期时间）
- [x] 记忆系统实现（缓冲记忆 + JSON持久化）
- [x] 规划模块实现
- [x] Agent核心循环
- [x] 78个测试全部通过
- [x] 调试模式（带时间戳的可观测日志）

---

## 后续扩展计划

1. **向量记忆**: 使用向量数据库存储长期记忆
2. **网络搜索**: 集成搜索引擎API
3. **复杂规划**: 使用LLM分解复杂任务
4. **多Agent协作**: 多个Agent协同工作
5. **工具扩展**: 添加更多工具（数据库、API调用等）
6. **Web UI**: 添加Web界面

---

> **注意**: 本项目为学习项目，代码未经人工验证，仅供参考学习使用。后续功能增量添加，README文档同步更新。
