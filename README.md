# MySelfAgent - LangChain Agent 系统

基于 LangChain 的智能 Agent 系统，支持任务分解、执行和评估。

## 项目结构

```
myselfagent/
├── main.py                 # 主入口文件
├── config.py               # 配置文件
├── requirements.txt        # 依赖包
├── pytest.ini             # 测试配置
├── README.md              # 项目说明
├── .gitignore             # Git忽略文件
├── .env.example           # 环境变量示例
│
├── src/                   # 源代码目录
│   ├── agent.py           # Agent核心类
│   ├── llm.py             # LLM接口
│   ├── templates.py       # HTML模板库
│   ├── verification.py    # 验证模块
│   ├── memory/            # 记忆模块
│   │   ├── base.py        # 基础记忆类
│   │   ├── buffer.py      # 缓冲记忆
│   │   └── context_manager.py  # 上下文管理
│   └── planner/           # 规划模块
│       ├── llm_planner.py # LLM规划器
│       └── simple.py      # 简单规划器
│
├── tests/                 # 测试目录
│   ├── test_agent.py      # Agent测试
│   ├── test_llm.py        # LLM测试
│   ├── test_memory/       # 记忆测试
│   ├── test_planner/      # 规划器测试
│   └── test_tools/        # 工具测试
│
├── examples/              # 示例文件
│   ├── demo.py            # 演示脚本
│   └── full_test.py       # 完整测试
│
├── docs/                  # 文档目录
│   ├── OPUS-5.md          # OPUS-5分析
│   ├── full_analysis.txt  # 完整分析报告
│   └── optimization_report.txt  # 优化报告
│
├── prompt/                # 提示词分析
│   ├── ab_test.py         # A/B测试脚本
│   ├── ab_test_report.txt # A/B测试报告
│   └── opus5_segments.txt # OPUS-5分段
│
└── logs/                  # 日志目录
    └── agent_log_*.txt    # Agent执行日志
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行Agent

```bash
# 基本运行
python main.py "你的任务描述"

# 调试模式
python main.py -d "你的任务描述"

# 导出日志
python main.py -d -e -l result.txt "你的任务描述"

# 交互模式
python main.py -i -d -e
```

### 命令行参数

| 参数 | 简写 | 说明 |
|------|------|------|
| `--interactive` | `-i` | 交互模式 |
| `--debug` | `-d` | 调试模式 |
| `--export-log` | `-e` | 导出日志 |
| `--log-path` | `-l` | 指定日志路径 |

## 功能特性

- ✅ 任务分解与规划
- ✅ LLM驱动的决策
- ✅ 工具调用（Python执行、文件操作、搜索）
- ✅ 记忆管理
- ✅ 结果评估与重试
- ✅ 日志导出
- ✅ 模板补充
- ✅ 验证循环

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试
python -m pytest tests/test_agent.py -v
```

## 配置

编辑 `config.py` 或创建 `.env` 文件：

```python
LLM_API_BASE = "http://127.0.0.1:8788/v1"
LLM_MODEL_NAME = "oxx"
```

## 许可证

MIT License
