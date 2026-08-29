# MySelfAgent - LangChain Agent 学习项目

## 项目简介

这是一个基于 LangChain 的 Agent 系统学习项目，采用 **TDD（测试驱动开发）** 方式构建。

### 核心架构

`
┌─────────────────────────────────────────────────────────────┐
│                          Agent                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │   LLM   │  │  工具    │  │  记忆    │  │  规划    │       │
│  │ (决策)  │  │ (执行)  │  │ (存储)  │  │ (分解)  │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
└─────────────────────────────────────────────────────────────┘
`

### 工作流程

`
规划 -> 决策 -> 执行 -> 结果存入记忆 -> 再决策 -> ... -> 任务完成
`

## 快速开始

### 1. 环境准备

`ash
# 克隆项目
git clone https://github.com/tripodxu/myselfagent.git
cd myselfagent

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
`

### 2. 配置

复制 .env.example 为 .env 并修改配置：

`ash
cp .env.example .env
`

主要配置项：
- LLM_API_BASE: 本地API地址（默认: http://127.0.0.1:8788）
- LLM_API_PATH: API路径（默认: /v1/responses）
- LLM_MODEL_NAME: 模型名称

### 3. 运行演示

`ash
# 运行演示
python examples/demo.py

# 使用主入口
python main.py "创建一个计算器"

# 交互模式
python main.py --interactive
`

### 4. 运行测试

`ash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/test_llm.py

# 运行并显示覆盖率
pytest --cov=src

# 详细输出
pytest -v
`

## 项目结构

`
myselfagent/
├── main.py                 # 主入口
├── requirements.txt        # 依赖包
├── config.py              # 配置文件
├── README.md              # 本文档
├── .env.example           # 环境变量示例
├── pytest.ini             # pytest配置
├── src/                   # 源代码
│   ├── llm.py             # LLM模块
│   ├── agent.py           # Agent核心
│   ├── tools/             # 工具系统
│   │   ├── base.py        # 工具基类
│   │   ├── python_exec.py # Python执行工具
│   │   ├── file_io.py     # 文件读写工具
│   │   └── search.py      # 搜索工具
│   ├── memory/            # 记忆系统
│   │   ├── base.py        # 记忆基类
│   │   └── buffer.py      # 缓冲记忆实现
│   └── planner/           # 规划模块
│       └── simple.py      # 简单规划器
├── tests/                 # 测试目录
│   ├── test_llm.py
│   ├── test_agent.py
│   ├── test_tools/
│   ├── test_memory/
│   └── test_planner/
└── examples/
    └── demo.py            # 演示脚本
`

## 模块详解

### 1. LLM 模块 (src/llm.py)

自定义LLM类，连接本地API：

`python
from src.llm import LocalLLM

llm = LocalLLM(
    api_base="http://127.0.0.1:8788",
    api_path="/v1/responses",
    model_name="default"
)
`

**特性：**
- 自动重试机制
- 超时处理
- 兼容OpenAI格式

### 2. 工具系统 (src/tools/)

**Python执行工具** - 安全执行Python代码：
`python
from src.tools.python_exec import PythonExecTool

tool = PythonExecTool(timeout=10)
result = tool.execute(code="print('Hello')")
`

**文件IO工具** - 文件读写操作：
`python
from src.tools.file_io import FileIOTool

tool = FileIOTool(allowed_paths=["."])
result = tool.execute(action="read", path="test.txt")
`

**搜索工具** - 文本搜索：
`python
from src.tools.search import SearchTool

tool = SearchTool()
result = tool.execute(action="text", pattern="keyword", text="content")
`

### 3. 记忆系统 (src/memory/)

缓冲记忆实现：

`python
from src.memory.buffer import BufferMemory

memory = BufferMemory(max_size=100, persist_path="memory.json")
memory.add_message("user", "Hello")
history = memory.get_history()
`

**特性：**
- 自动持久化到JSON文件
- 上下文窗口管理
- 消息搜索

### 4. 规划模块 (src/planner/)

简单规划器：

`python
from src.planner.simple import SimplePlanner

planner = SimplePlanner(max_steps=5)
plan = planner.create_plan("完成某项任务")
next_step = planner.get_next_step(plan_id)
`

### 5. Agent 核心 (src/agent.py)

整合所有模块：

`python
from src.agent import Agent

agent = Agent(
    llm=llm,
    memory=memory,
    planner=planner,
    tool_registry=tool_registry
)

result = agent.run("执行某个任务")
`

## TDD 学习笔记

### 什么是 TDD？

TDD（测试驱动开发）是一种开发方法：
1. **Red**: 先写失败的测试
2. **Green**: 写最少的代码让测试通过
3. **Refactor**: 重构代码

### 本项目的TDD实践

每个模块都遵循TDD流程：

1. **LLM模块**: 6个测试覆盖初始化、调用、重试、超时
2. **工具基类**: 10个测试覆盖工具注册、获取、列表
3. **Python执行工具**: 8个测试覆盖执行、错误、安全限制
4. **文件IO工具**: 8个测试覆盖读写、权限、路径安全
5. **搜索工具**: 11个测试覆盖文本、文件、正则、过滤
6. **记忆系统**: 16个测试覆盖存储、检索、持久化
7. **规划模块**: 9个测试覆盖创建、更新、完成
8. **Agent核心**: 10个测试覆盖初始化、执行、错误处理

**总计: 78个测试，全部通过**

## 后续扩展

### 可添加的功能

1. **向量记忆**: 使用向量数据库存储长期记忆
2. **网络搜索**: 集成搜索引擎API
3. **复杂规划**: 使用LLM分解复杂任务
4. **多Agent协作**: 多个Agent协同工作
5. **工具扩展**: 添加更多工具（数据库、API调用等）
6. **对话界面**: 添加Web UI或命令行界面

### 扩展示例

`python
# 添加新工具
class DatabaseTool(BaseTool):
    def __init__(self):
        super().__init__("database", "数据库操作")
    
    def execute(self, query: str, **kwargs):
        # 实现数据库操作
        pass

# 注册到Agent
agent.tool_registry.register(DatabaseTool())
`

## 常见问题

### Q: 如何连接本地API？

A: 确保本地API服务正在运行，并在 .env 中配置正确的地址和端口。

### Q: 如何添加新工具？

A: 继承 BaseTool 类，实现 xecute 方法，然后注册到 ToolRegistry。

### Q: 如何自定义规划逻辑？

A: 修改 SimplePlanner._decompose_goal() 方法，或创建新的规划器类。

## 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

---

## 学习日志

### 第一阶段：最小可用版本 (2026-08-29)

**完成内容：**
- ✅ 项目结构搭建
- ✅ LLM模块实现
- ✅ 工具系统实现（Python执行、文件IO、搜索）
- ✅ 记忆系统实现
- ✅ 规划模块实现
- ✅ Agent核心循环
- ✅ 78个测试全部通过

**学习心得：**
- TDD让代码更可靠
- 模块化设计便于扩展
- 测试是最好的文档

**下一步：**
- 连接真实LLM API测试
- 添加更多工具
- 优化规划算法
