import os
from dotenv import load_dotenv

load_dotenv()

# LLM配置
LLM_API_BASE = os.getenv("LLM_API_BASE", "http://127.0.0.1:8788")
LLM_API_PATH = os.getenv("LLM_API_PATH", "/v1/responses")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "mimo-v2.5-pro")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))

# 工具配置
PYTHON_EXEC_TIMEOUT = int(os.getenv("PYTHON_EXEC_TIMEOUT", "10"))
FILE_IO_ALLOWED_PATHS = os.getenv("FILE_IO_ALLOWED_PATHS", ".").split(",")

# 记忆配置
MEMORY_CONTEXT_WINDOW = int(os.getenv("MEMORY_CONTEXT_WINDOW", "10"))
MEMORY_PERSIST_PATH = os.getenv("MEMORY_PERSIST_PATH", "memory.json")

# 规划配置
PLANNER_MAX_STEPS = int(os.getenv("PLANNER_MAX_STEPS", "10"))
