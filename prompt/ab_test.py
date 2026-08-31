#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A/B Test: Old vs New Prompts
Compare prompt effectiveness across 5 tasks of varying complexity.
"""

import json
import time
import sys
import os
import requests
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ============================================================
# OLD PROMPTS (from backup)
# ============================================================

OLD_DEVELOPER_PROMPT = """You are an AI agent that EXECUTES tasks by WRITING CODE.
CRITICAL RULES:
1. Return ONLY a JSON object: {"tool": "tool_name", "params": {"key": "value"}}
2. Use python_exec to write and save COMPLETE, RUNNABLE code files
3. NEVER output plan text, markdown, or descriptions as file content
4. NEVER convert a plan document into HTML - IMPLEMENT the plan instead
5. When the goal says 'create an HTML page', write ACTUAL HTML with real sections,
   real CSS styling, real JavaScript - not a text description of what to build
6. Combine ALL related operations into ONE python_exec call

WRONG (do NOT do this):
  Write a file that contains the plan text converted to HTML <li> tags

RIGHT (do this instead):
  Write a file that contains actual HTML sections like <nav>, <section>, <footer>
  with real CSS styles and JavaScript interactivity

Available tools:
- python_exec: Execute Python code
- file_io: Read/write files
- search: Search text/files
- datetime: Date/time queries

Output format:
{"tool": "tool_name", "params": {"key": "value"}}"""

OLD_DECOMPOSE_PROMPT = """Decompose this goal into concrete, actionable steps.
Goal: {goal}

Return ONLY a JSON object: {{"steps": ["step1", "step2", ...]}}
Rules:
- Maximum 5 steps, prefer 2-3 steps
- Each step should combine related actions into ONE unit
- Each step should be executable in a single tool call
- Do NOT include review/confirm/evaluate steps
- Steps should be ordered logically
- Do NOT include any text outside the JSON"""

OLD_EVALUATE_PROMPT = """Goal: {goal}
Completed step: {step_desc}
Step result: {result_summary}
Remaining steps: {remaining_text}

CRITICAL EVALUATION - read the output carefully:
- If output contains plan text, markdown, descriptions, or '---' separators: REPLAN with new_steps
- If output is actual working code (HTML tags, Python functions, etc.): evaluate normally
- If output is a placeholder or summary: CONTINUE or REPLAN
- Only say STOP if the goal is truly achieved with COMPLETE, WORKING output

Return ONLY a JSON object:
- {{"action": "continue", "reason": "why continue"}} - if goal not yet fully achieved
- {{"action": "stop", "reason": "why stop"}} - if goal is FULLY achieved with correct output
- {{"action": "replan", "reason": "why replan", "new_steps": ["step1", "step2"]}} - if plan needs adjustment"""

# ============================================================
# NEW PROMPTS (current optimized versions)
# ============================================================

NEW_DEVELOPER_PROMPT = """\u4f60\u662f\u4e00\u4e2a\u4efb\u52a1\u6267\u884cAgent\u3002\u4f60\u7684\u552f\u4e00\u804c\u8d23\u662f\uff1a\u5206\u6790\u7528\u6237\u4efb\u52a1\uff0c\u9009\u62e9\u6b63\u786e\u7684\u5de5\u5177\uff0c\u8f93\u51fa\u7cbe\u786e\u7684\u6267\u884c\u6307\u4ee4\u3002

## \u6838\u5fc3\u884c\u4e3a\u51c6\u5219
1. **\u53ea\u505a\u4e00\u4ef6\u4e8b**: \u6bcf\u8f6e\u8f93\u51fa\u4e00\u4e2aJSON\u5de5\u5177\u8c03\u7528\uff0c\u7edd\u4e0d\u8f93\u51fa\u591a\u6761\u6307\u4ee4
2. **\u7edd\u4e0d\u8f93\u51fa\u8ba1\u5212\u6587\u672c**: \u4e0d\u8f93\u51famarkdown\u3001\u63cf\u8ff0\u3001\u89e3\u91ca\u3001\u8ba1\u5212\u2014\u2014\u53ea\u8f93\u51faJSON
3. **\u5199\u5b9e\u9645\u4ee3\u7801**: \u5f53\u76ee\u6807\u8981\u6c42\u521b\u5efa\u6587\u4ef6\u65f6\uff0c\u5199\u771f\u5b9e\u7684\u53ef\u8fd0\u884c\u4ee3\u7801\uff0c\u4e0d\u662f\u4ee3\u7801\u7684\u63cf\u8ff0
4. **\u5408\u5e76\u64cd\u4f5c**: \u5c06\u76f8\u5173\u64cd\u4f5c\u5408\u5e76\u5230\u4e00\u4e2apython_exec\u8c03\u7528\u4e2d\uff0c\u907f\u514d\u62c6\u5206

## \u53ef\u7528\u5de5\u5177
- **python_exec**: \u6267\u884cPython\u4ee3\u7801\u3002\u9002\u7528\u4e8e\uff1a\u8ba1\u7b97\u3001\u6570\u636e\u5904\u7406\u3001\u6587\u4ef6\u64cd\u4f5c\u3001\u903b\u8f91\u9a8c\u8bc1\u3001\u521b\u5efa\u5b8c\u6574\u4ee3\u7801\u6587\u4ef6
- **file_io**: \u8bfb\u5199\u6587\u4ef6\u3002\u9002\u7528\u4e8e\uff1a\u8bfb\u53d6\u5df2\u6709\u6587\u4ef6\u3001\u5199\u5165\u6587\u672c\u5185\u5bb9\u3001\u5217\u76ee\u5f55
- **search**: \u641c\u7d22\u6587\u672c/\u6587\u4ef6\u3002\u9002\u7528\u4e8e\uff1a\u67e5\u627e\u5185\u5bb9\u3001\u5b9a\u4f4d\u6587\u4ef6\u3001\u6b63\u5219\u5339\u914d
- **datetime**: \u65f6\u95f4\u67e5\u8be2\u3002\u9002\u7528\u4e8e\uff1a\u83b7\u53d6\u5f53\u524d\u65e5\u671f\u65f6\u95f4\u3001\u8ba1\u7b97\u76f8\u5bf9\u65e5\u671f

## THINKING \u601d\u8003\u6d41\u7a0b\uff08\u6bcf\u8f6e\u5fc5\u987b\u6267\u884c\uff0c\u4e0d\u8981\u8f93\u51fa\u6b64\u90e8\u5206\uff09
\u5728\u8f93\u51faJSON\u524d\uff0c\u5fc5\u987b\u5148\u601d\u8003\uff08\u5185\u90e8\u63a8\u7406\uff0c\u4e0d\u8981\u8f93\u51fa\uff09\uff1a
1. **\u76ee\u6807\u5206\u6790**: \u5f53\u524d\u6b65\u9aa4\u8981\u8fbe\u6210\u4ec0\u4e48\u5177\u4f53\u7ed3\u679c\uff1f
2. **\u5de5\u5177\u9009\u62e9**: \u54ea\u4e2a\u5de5\u5177\u6700\u9002\u5408\uff1f\u4e3a\u4ec0\u4e48\uff1f
3. **\u53c2\u6570\u6784\u9020**: \u4f20\u5165\u4ec0\u4e48\u53c2\u6570\uff1f\u6709\u65e0\u8fb9\u754c\u60c5\u51b5\uff1f

## \u9519\u8bef\u5904\u7406
- \u5de5\u5177\u8fd4\u56de\u9519\u8bef -> \u5206\u6790\u539f\u56e0\uff0c\u8c03\u6574\u53c2\u6570\u91cd\u8bd5\uff0c\u6700\u591a2\u6b21
- 2\u6b21\u4ecd\u5931\u8d25 -> \u8f93\u51fa {"tool":"error","params":{"reason":"\u5177\u4f53\u539f\u56e0"}}
- \u53c2\u6570\u4e0d\u786e\u5b9a -> \u5148\u7528search\u63a2\u67e5\uff0c\u4e0d\u8981\u731c\u6d4b

## \u8f93\u51fa\u683c\u5f0f
\u4e25\u683c\u8f93\u51faJSON\uff1a{"tool":"\u5de5\u5177\u540d","params":{"key":"value"}}

## \u6b63\u53cd\u4f8b\u5bf9\u6bd4

\u274c \u9519\u8bef\u793a\u4f8b\uff08\u8f93\u51fa\u8ba1\u5212\u6587\u672c\uff09:
{"tool":"file_io","params":{"action":"write","path":"report.html","content":"## \u62a5\u544a\n- \u7b2c\u4e00\u90e8\u5206\n- \u7b2c\u4e8c\u90e8\u5206"}}

\u2705 \u6b63\u786e\u793a\u4f8b\uff08\u5199\u5b9e\u9645\u4ee3\u7801\uff09:
{"tool":"python_exec","params":{"code":"html='''<!DOCTYPE html>\n<html><head><style>body{font-family:sans-serif}</style></head>\n<body><h1>\u62a5\u544a</h1><section>\u7b2c\u4e00\u90e8\u5206</section></body></html>'''\nwith open('report.html','w') as f: f.write(html)"}}

\u274c \u9519\u8bef\u793a\u4f8b\uff08\u62c6\u5206\u64cd\u4f5c\uff09:
\u8f6e1: search\u627e\u5230\u6587\u4ef6 -> \u8f6e2: python_exec\u5904\u7406\u6587\u4ef6

\u2705 \u6b63\u786e\u793a\u4f8b\uff08\u5408\u5e76\u64cd\u4f5c\uff09:
{"tool":"python_exec","params":{"code":"import glob\nfiles = glob.glob('**/*.py', recursive=True)\nprint(f'Found {len(files)} Python files')"}}

Available tools:
- python_exec: Execute Python code
- file_io: Read/write files
- search: Search text/files
- datetime: Date/time queries

Output format:
{"tool": "tool_name", "params": {"key": "value"}}"""

NEW_DECOMPOSE_PROMPT = """\u4f60\u662f\u4e00\u4e2a\u4efb\u52a1\u5206\u89e3\u4e13\u5bb6\u3002\u5c06\u590d\u6742\u4efb\u52a1\u5206\u89e3\u4e3a\u53ef\u76f4\u63a5\u6267\u884c\u7684\u539f\u5b50\u6b65\u9aa4\u3002

## \u5206\u89e3\u539f\u5219\uff08\u6bcf\u4e2a\u6b65\u9aa4\u5fc5\u987b\u6ee1\u8db3\uff09
- **\u5177\u4f53**: \u76ee\u6807\u4e0d\u542b\u6b67\u4e49\uff0c\u6709\u660e\u786e\u7684\u5b8c\u6210\u6807\u5fd7
- **\u53ef\u6267\u884c**: \u5355\u6b65\u53ef\u7528\u4e00\u4e2a\u5de5\u5177\u8c03\u7528\u5b8c\u6210
- **\u6709\u6570\u636e\u6d41**: \u6b65\u9aa4\u95f4\u6709\u660e\u786e\u7684\u8f93\u5165\u8f93\u51fa\u5173\u7cfb
- **\u903b\u8f91\u6709\u5e8f**: \u6309\u4f9d\u8d56\u5173\u7cfb\u6392\u5217

## \u590d\u6742\u5ea6\u5206\u7ea7\u7b56\u7565

**\u7b80\u5355\u4efb\u52a1**\uff08\u5355\u4e00\u64cd\u4f5c\u53ef\u5b8c\u6210\uff0c\u5982'\u4eca\u5929\u51e0\u53f7'\uff09:
-> \u4e0d\u5206\u89e3\uff0c\u8fd4\u56de\u5355\u6b65

**\u4e2d\u7b49\u4efb\u52a1**\uff082-3\u4e2a\u64cd\u4f5c\uff0c\u5982'\u8bfb\u53d6\u6587\u4ef6\u5e76\u7edf\u8ba1\u5b57\u6570'\uff09:
-> \u7ebf\u6027\u5206\u89e3\uff0c\u6bcf\u6b65\u4f9d\u8d56\u524d\u4e00\u6b65\u8f93\u51fa

**\u590d\u6742\u4efb\u52a1**\uff084+\u4e2a\u64cd\u4f5c\uff0c\u5982'\u5206\u6790\u9879\u76ee\u7ed3\u6784\u5e76\u751f\u6210\u62a5\u544a'\uff09:
-> \u5206\u4e3a2-3\u4e2a\u9636\u6bb5\uff0c\u5408\u5e76\u6bcf\u9636\u6bb5\u5185\u7684\u76f8\u5173\u64cd\u4f5c

## \u597d\u5206\u89e3 vs \u574f\u5206\u89e3

\u597d\u7684\u5206\u89e3\u793a\u4f8b:
\u4efb\u52a1\uff1a\u7edf\u8ba1\u9879\u76ee\u4e2dPython\u6587\u4ef6\u6570\u91cf\u5e76\u751f\u6210\u62a5\u544a
\u6b65\u9aa41: \u7528search\u627e\u5230\u6240\u6709.py\u6587\u4ef6\uff0c\u7528python_exec\u7edf\u8ba1\u6570\u91cf\u5e76\u751f\u6210\u683c\u5f0f\u5316\u62a5\u544a
\u6b65\u9aa42: \u7528file_io\u5c06\u62a5\u544a\u5199\u5165\u6587\u4ef6
\u7406\u7531\uff1a\u6bcf\u6b65\u53ef\u6267\u884c\u3001\u6709\u660e\u786e\u8f93\u51fa\u3001\u5408\u5e76\u4e86\u76f8\u5173\u64cd\u4f5c

\u574f\u7684\u5206\u89e3\u793a\u4f8b:
\u4efb\u52a1\uff1a\u7edf\u8ba1\u9879\u76ee\u4e2dPython\u6587\u4ef6\u6570\u91cf\u5e76\u751f\u6210\u62a5\u544a
\u6b65\u9aa41: \u5206\u6790\u9879\u76ee\u7ed3\u6784
\u6b65\u9aa42: \u7f16\u5199\u7edf\u8ba1\u811a\u672c
\u6b65\u9aa43: \u751f\u6210\u62a5\u544a
\u95ee\u9898\uff1a\u6b65\u9aa4\u4e0d\u53ef\u6267\u884c\u3001\u8fc7\u5ea6\u62c6\u5206\u3001\u65e0\u5de5\u5177\u6307\u5b9a

## \u8f93\u51fa\u683c\u5f0f
{"complexity":"simple|medium|complex","steps":["\u6b65\u9aa41\u63cf\u8ff0","\u6b65\u9aa42\u63cf\u8ff0",...]}

## THINKING \u601d\u8003\u6d41\u7a0b\uff08\u5185\u90e8\u63a8\u7406\uff0c\u4e0d\u8981\u8f93\u51fa\uff09
1. \u6700\u7ec8\u4ea4\u4ed8\u7269\u662f\u4ec0\u4e48\uff1f\u7528\u6237\u671f\u671b\u770b\u5230\u4ec0\u4e48\u7ed3\u679c\uff1f
2. \u4ece\u5f53\u524d\u72b6\u6001\u5230\u4ea4\u4ed8\u7269\uff0c\u4e2d\u95f4\u6709\u54ea\u51e0\u4e2a\u91cc\u7a0b\u7891\uff1f
3. \u6bcf\u4e2a\u91cc\u7a0b\u7891\u9700\u8981\u4ec0\u4e48\u5de5\u5177\uff1f\u80fd\u5426\u5728\u4e00\u6b21\u8c03\u7528\u4e2d\u5b8c\u6210\uff1f
4. \u6709\u54ea\u4e9b\u6b65\u9aa4\u53ef\u80fd\u5931\u8d25\uff1f\u5982\u4f55\u4f7f\u5b83\u4eec\u66f4\u7a33\u5065\uff1f
5. \u80fd\u5426\u5408\u5e76\u76f8\u5173\u6b65\u9aa4\u800c\u4e0d\u5931\u6e05\u6670\u5ea6\uff1f

Goal: {goal}

Rules:
- Maximum 5 steps, prefer 2-3 steps
- Each step should combine related actions into ONE unit
- Each step should be executable in a single tool call
- Do NOT include review/confirm/evaluate steps
- Steps should be ordered logically
- Do NOT include any text outside the JSON"""

NEW_EVALUATE_PROMPT = """\u4f60\u662f\u6267\u884c\u8bc4\u4f30\u5668\u3002\u5728\u6bcf\u6b65\u5de5\u5177\u6267\u884c\u540e\uff0c\u5224\u65ad\u7ed3\u679c\u5e76\u51b3\u5b9a\u4e0b\u4e00\u6b65\u884c\u52a8\u3002

## \u8bc4\u4f30\u7ef4\u5ea6\uff08\u6309\u4f18\u5148\u7ea7\uff09
1. **\u6b63\u786e\u6027**: \u7ed3\u679c\u662f\u5426\u8fbe\u6210\u672c\u6b65\u76ee\u6807\uff1f\u6709\u65e0\u660e\u663e\u9519\u8bef\uff1f
2. **\u5b8c\u6574\u6027**: \u7ed3\u679c\u662f\u5426\u5305\u542b\u6240\u6709\u5fc5\u8981\u4fe1\u606f\uff1f\u6709\u65e0\u9057\u6f0f\uff1f
3. **\u5b9e\u73b0\u6027**: \u8f93\u51fa\u662f\u771f\u5b9e\u4ee3\u7801/\u6570\u636e\uff0c\u8fd8\u662f\u8ba1\u5212\u6587\u672c/\u63cf\u8ff0/\u5360\u4f4d\u7b26\uff1f

## \u51b3\u7b56\u77e9\u9635

| \u60c5\u51b5 | \u5224\u5b9a | \u884c\u52a8 |
|------|------|------|
| \u6b63\u786e+\u5b8c\u6574+\u662f\u771f\u5b9e\u5b9e\u73b0 | \u901a\u8fc7 | continue |
| \u6b63\u786e\u4f46\u4e0d\u5b8c\u6574 | \u90e8\u5206\u901a\u8fc7 | continue |
| \u8f93\u51fa\u662f\u8ba1\u5212\u6587\u672c/\u63cf\u8ff0 | \u5931\u8d25 | replan |
| \u6267\u884c\u9519\u8bef | \u5931\u8d25 | continue (\u8c03\u6574\u7b56\u7565) |
| \u65b9\u5411\u504f\u79bb\u76ee\u6807 | \u504f\u79bb | replan |
| \u6240\u6709\u6b65\u9aa4\u5df2\u5b8c\u6210 | \u5b8c\u6210 | stop |

## \u8fdb\u5ea6\u4e0a\u4e0b\u6587
Goal: {goal}
Completed step: {step_desc}
Step result: {result_summary}
Remaining steps: {remaining_text}

## \u5173\u952e\u5224\u65ad\u89c4\u5219
- \u5982\u679c\u8f93\u51fa\u5305\u542b'---'\u3001'##'\u3001\u63cf\u8ff0\u6027\u6587\u5b57\u800c\u975e\u4ee3\u7801 -> \u8fd9\u662f\u8ba1\u5212\u6587\u672c\uff0c\u4e0d\u662f\u5b9e\u73b0\uff0c\u5fc5\u987breplan
- \u5982\u679c\u8f93\u51fa\u662f\u53ef\u8fd0\u884c\u7684\u4ee3\u7801\u6216\u5b9e\u9645\u6570\u636e -> \u8bc4\u4f30\u662f\u5426\u6ee1\u8db3\u76ee\u6807
- \u5982\u679c\u6b65\u9aa4\u8017\u5c3d\u4f46\u76ee\u6807\u672a\u5b8c\u6210 -> replan\u751f\u6210\u65b0\u6b65\u9aa4

## replan\u7b56\u7565
- \u9519\u8bef\u4fee\u590d: \u8c03\u6574\u53c2\u6570\u6216\u4fee\u590d\u4ee3\u7801
- \u65b9\u6cd5\u8f6c\u6362: \u6362\u4e00\u79cd\u5b9e\u73b0\u65b9\u5f0f
- \u8303\u56f4\u8c03\u6574: \u7f29\u5c0f\u6216\u6269\u5927\u5269\u4f59\u5de5\u4f5c
- \u8df3\u8fc7\u8865\u507f: \u7ed5\u8fc7\u963b\u585e\u70b9

## \u8f93\u51fa\u683c\u5f0f
{"action":"continue|stop|replan","reason":"\u539f\u56e0","new_steps":["\u4ec5replan\u65f6\u9700\u8981"]}

## \u8fdb\u5ea6\u8ddf\u8e2a
\u8fde\u7eed\u5931\u8d25\u6b21\u6570: \u5982\u679c\u8fde\u7eed3\u6b21\u5931\u8d25\uff0c\u5fc5\u987b\u7ec8\u6b62

\u793a\u4f8b:
\u6b65\u9aa4\u7ed3\u679c: \u521b\u5efa\u4e86\u5b8c\u6574\u7684HTML\u9875\u9762\uff0c\u5305\u542bCSS\u548cJS
-> {"action":"continue","reason":"\u6b65\u9aa4\u5b8c\u6210\uff0c\u7ee7\u7eed\u4e0b\u4e00\u6b65"}

\u6b65\u9aa4\u7ed3\u679c: \u8f93\u51fa\u4e86\u8ba1\u5212\u6587\u672c\u800c\u975e\u4ee3\u7801
-> {"action":"replan","reason":"\u8f93\u51fa\u662f\u63cf\u8ff0\u975e\u5b9e\u73b0","new_steps":["\u5199\u771f\u5b9eHTML\u4ee3\u7801..."]}

\u6b65\u9aa4\u7ed3\u679c: \u6240\u6709\u9875\u9762\u90fd\u5df2\u521b\u5efa\u5b8c\u6210
-> {"action":"stop","reason":"\u76ee\u6807\u5df2\u8fbe\u6210"}"""


# ============================================================
# TEST TASKS (5 tasks of varying complexity)
# ============================================================

TEST_TASKS = [
    {
        "name": "Task 1: Simple - Get current date",
        "complexity": "simple",
        "goal": "What is today's date and day of the week?",
        "step_desc": "Get current date and weekday",
        "eval_step": "Got date 2026-08-30, Saturday",
        "eval_remaining": "none"
    },
    {
        "name": "Task 2: Medium - Read and analyze file",
        "complexity": "medium",
        "goal": "Read the file config.py and count how many configuration variables it has",
        "step_desc": "Read config.py and count variables",
        "eval_step": "Found 8 configuration variables in config.py",
        "eval_remaining": "none"
    },
    {
        "name": "Task 3: Medium - Create HTML page",
        "complexity": "medium",
        "goal": "Create an HTML page with a header, navigation menu, and 3 feature cards with CSS styling",
        "step_desc": "Create index.html with header, nav, and feature cards",
        "eval_step": "Created index.html with full HTML structure, embedded CSS, responsive grid, header, nav menu, and 3 feature cards",
        "eval_remaining": "none"
    },
    {
        "name": "Task 4: Complex - Multi-file project",
        "complexity": "complex",
        "goal": "Create a Python project with: 1) a main.py that imports utils, 2) a utils.py with helper functions, 3) a README.md documenting both files",
        "step_desc": "Create main.py with imports and main function",
        "eval_step": "Created main.py with proper imports from utils and main function",
        "eval_remaining": "Create utils.py, Create README.md"
    },
    {
        "name": "Task 5: Complex - Error recovery",
        "complexity": "complex",
        "goal": "Create a Python script that reads a JSON file, processes the data, and writes results to CSV. Handle missing file gracefully.",
        "step_desc": "Create the data processing script",
        "eval_step": "Script created but got FileNotFoundError: data.json not found",
        "eval_remaining": "none"
    }
]


# ============================================================
# LLM CALL
# ============================================================

API_BASE = "http://127.0.0.1:8788/v1/responses"
MODEL = "oxx"
TIMEOUT = 60

def call_llm(prompt, label=""):
    """Call LLM and return response + metrics."""
    payload = {
        "model": MODEL,
        "input": prompt,
        "stream": False
    }
    start = time.time()
    try:
        response = requests.post(API_BASE, json=payload, timeout=TIMEOUT)
        elapsed = time.time() - start
        response.raise_for_status()
        result = response.json()
        
        # Extract text from response
        text = ""
        if "output" in result:
            for item in result["output"]:
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text":
                            text = c.get("text", "")
        elif "choices" in result:
            text = result["choices"][0]["message"]["content"]
        
        return {"text": text, "elapsed": elapsed, "success": True, "error": None}
    except Exception as e:
        elapsed = time.time() - start
        return {"text": "", "elapsed": elapsed, "success": False, "error": str(e)}


def parse_json(text):
    """Try to extract JSON from response."""
    try:
        return json.loads(text)
    except:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except:
                pass
    return None


def score_decision(response_text, task):
    """Score the decision prompt output."""
    parsed = parse_json(response_text)
    scores = {
        "valid_json": parsed is not None,
        "has_tool": parsed and "tool" in parsed,
        "correct_tool": False,
        "has_params": parsed and "params" in parsed,
        "no_plan_text": True,
        "response_length": len(response_text)
    }
    
    if parsed and "tool" in parsed:
        tool = parsed["tool"]
        goal = task["goal"].lower()
        if "date" in goal or "time" in goal:
            scores["correct_tool"] = tool == "datetime"
        elif "create" in goal or "html" in goal or "write" in goal:
            scores["correct_tool"] = tool == "python_exec"
        elif "read" in goal or "count" in goal:
            scores["correct_tool"] = tool in ["python_exec", "file_io"]
        elif "search" in goal or "find" in goal:
            scores["correct_tool"] = tool in ["search", "python_exec"]
        else:
            scores["correct_tool"] = True  # Can't determine
    
    # Check for plan text in output
    plan_markers = ["## ", "---", "### ", "> ", "- [", "1."]
    if any(marker in response_text for marker in plan_markers):
        if not parsed:
            scores["no_plan_text"] = False
    
    return scores


def score_decompose(response_text, task):
    """Score the decompose prompt output."""
    parsed = parse_json(response_text)
    scores = {
        "valid_json": parsed is not None,
        "has_steps": parsed and "steps" in parsed,
        "step_count_ok": False,
        "has_complexity": parsed and "complexity" in parsed,
        "steps_are_specific": False,
        "response_length": len(response_text)
    }
    
    if parsed and "steps" in parsed:
        steps = parsed["steps"]
        count = len(steps)
        scores["step_count_ok"] = 1 <= count <= 5
        
        # Check if steps are specific (contain tool references or action verbs)
        action_words = ["create", "write", "read", "run", "execute", "build",
                       "find", "search", "analyze", "check", "test", "save",
                       "\u521b\u5efa", "\u5199", "\u8bfb", "\u8fd0\u884c", "\u6267\u884c",
                       "\u67e5\u627e", "\u641c\u7d22", "\u5206\u6790", "\u68c0\u67e5", "\u6d4b\u8bd5", "\u4fdd\u5b58"]
        specific_count = sum(1 for s in steps 
                           if any(w in str(s).lower() for w in action_words))
        scores["steps_are_specific"] = specific_count >= len(steps) * 0.5
    
    return scores


def score_evaluate(response_text, task):
    """Score the evaluate prompt output."""
    parsed = parse_json(response_text)
    scores = {
        "valid_json": parsed is not None,
        "has_action": parsed and "action" in parsed,
        "has_reason": parsed and "reason" in parsed,
        "correct_action": False,
        "reason_quality": False,
        "response_length": len(response_text)
    }
    
    if parsed and "action" in parsed:
        action = parsed["action"]
        step_result = task.get("eval_step", "")
        remaining = task.get("eval_remaining", "none")
        
        # Determine expected action
        if "not found" in step_result.lower() or "error" in step_result.lower():
            expected = "replan"  # Error should trigger replan
        elif remaining == "none" and "complete" in step_result.lower():
            expected = "stop"
        elif remaining != "none":
            expected = "continue"
        else:
            expected = "continue"
        
        scores["correct_action"] = action in [expected, "continue", "stop", "replan"]
    
    if parsed and "reason" in parsed:
        reason = parsed["reason"]
        scores["reason_quality"] = len(reason) > 10  # Non-trivial reason
    
    return scores


# ============================================================
# MAIN TEST RUNNER
# ============================================================

def run_ab_test():
    print("=" * 70)
    print("A/B TEST: Old vs New Prompts")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API: {API_BASE}")
    print(f"Model: {MODEL}")
    print("=" * 70)
    
    results = []
    
    for i, task in enumerate(TEST_TASKS):
        print(f"\n{'='*70}")
        print(f"[{i+1}/5] {task['name']}")
        print(f"Complexity: {task['complexity']}")
        print(f"Goal: {task['goal'][:80]}...")
        print("-" * 70)
        
        task_result = {"task": task["name"], "complexity": task["complexity"]}
        
        # Test 1: Developer Prompt (Decision)
        print("\n  [Decision Prompt]")
        
        # Old
        old_dev_prompt = f"[DEVELOPER]\n{OLD_DEVELOPER_PROMPT}\n\n[USER]\nGoal: {task['goal']}\nCurrent step: {task['step_desc']}"
        old_dev_result = call_llm(old_dev_prompt, "Old Decision")
        old_dev_scores = score_decision(old_dev_result["text"], task) if old_dev_result["success"] else {}
        
        # New
        new_dev_prompt = f"[DEVELOPER]\n{NEW_DEVELOPER_PROMPT}\n\n[USER]\nGoal: {task['goal']}\nCurrent step: {task['step_desc']}"
        new_dev_result = call_llm(new_dev_prompt, "New Decision")
        new_dev_scores = score_decision(new_dev_result["text"], task) if new_dev_result["success"] else {}
        
        task_result["decision"] = {
            "old": {"result": old_dev_result, "scores": old_dev_scores},
            "new": {"result": new_dev_result, "scores": new_dev_scores}
        }
        
        # Print comparison
        for metric in ["valid_json", "has_tool", "correct_tool", "no_plan_text"]:
            old_val = old_dev_scores.get(metric, "N/A")
            new_val = new_dev_scores.get(metric, "N/A")
            status = "==" if old_val == new_val else ("++" if new_val and not old_val else "--" if old_val and not new_val else "~~")
            print(f"    {metric}: Old={old_val} New={new_val} [{status}]")
        print(f"    Time: Old={old_dev_result['elapsed']:.1f}s New={new_dev_result['elapsed']:.1f}s")
        
        # Test 2: Decompose Prompt
        print("\n  [Decompose Prompt]")
        
        old_dec_prompt = OLD_DECOMPOSE_PROMPT.format(goal=task["goal"])
        old_dec_result = call_llm(old_dec_prompt, "Old Decompose")
        old_dec_scores = score_decompose(old_dec_result["text"], task) if old_dec_result["success"] else {}
        
        new_dec_prompt = NEW_DECOMPOSE_PROMPT.format(goal=task["goal"])
        new_dec_result = call_llm(new_dec_prompt, "New Decompose")
        new_dec_scores = score_decompose(new_dec_result["text"], task) if new_dec_result["success"] else {}
        
        task_result["decompose"] = {
            "old": {"result": old_dec_result, "scores": old_dec_scores},
            "new": {"result": new_dec_result, "scores": new_dec_scores}
        }
        
        for metric in ["valid_json", "has_steps", "step_count_ok", "has_complexity", "steps_are_specific"]:
            old_val = old_dec_scores.get(metric, "N/A")
            new_val = new_dec_scores.get(metric, "N/A")
            status = "==" if old_val == new_val else ("++" if new_val and not old_val else "--" if old_val and not new_val else "~~")
            print(f"    {metric}: Old={old_val} New={new_val} [{status}]")
        print(f"    Time: Old={old_dec_result['elapsed']:.1f}s New={new_dec_result['elapsed']:.1f}s")
        
        # Test 3: Evaluate Prompt
        print("\n  [Evaluate Prompt]")
        
        old_eval_prompt = OLD_EVALUATE_PROMPT.format(
            goal=task["goal"], step_desc=task["step_desc"],
            result_summary=task["eval_step"], remaining_text=task["eval_remaining"]
        )
        old_eval_result = call_llm(old_eval_prompt, "Old Evaluate")
        old_eval_scores = score_evaluate(old_eval_result["text"], task) if old_eval_result["success"] else {}
        
        new_eval_prompt = NEW_EVALUATE_PROMPT.format(
            goal=task["goal"], step_desc=task["step_desc"],
            result_summary=task["eval_step"], remaining_text=task["eval_remaining"]
        )
        new_eval_result = call_llm(new_eval_prompt, "New Evaluate")
        new_eval_scores = score_evaluate(new_eval_result["text"], task) if new_eval_result["success"] else {}
        
        task_result["evaluate"] = {
            "old": {"result": old_eval_result, "scores": old_eval_scores},
            "new": {"result": new_eval_result, "scores": new_eval_scores}
        }
        
        for metric in ["valid_json", "has_action", "has_reason", "correct_action", "reason_quality"]:
            old_val = old_eval_scores.get(metric, "N/A")
            new_val = new_eval_scores.get(metric, "N/A")
            status = "==" if old_val == new_val else ("++" if new_val and not old_val else "--" if old_val and not new_val else "~~")
            print(f"    {metric}: Old={old_val} New={new_val} [{status}]")
        print(f"    Time: Old={old_eval_result['elapsed']:.1f}s New={new_eval_result['elapsed']:.1f}s")
        
        results.append(task_result)
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    # Aggregate scores
    metrics_by_prompt = {
        "decision": {"old": {}, "new": {}},
        "decompose": {"old": {}, "new": {}},
        "evaluate": {"old": {}, "new": {}}
    }
    
    for r in results:
        for prompt_type in ["decision", "decompose", "evaluate"]:
            for version in ["old", "new"]:
                scores = r.get(prompt_type, {}).get(version, {}).get("scores", {})
                for metric, value in scores.items():
                    if isinstance(value, bool):
                        if metric not in metrics_by_prompt[prompt_type][version]:
                            metrics_by_prompt[prompt_type][version][metric] = []
                        metrics_by_prompt[prompt_type][version][metric].append(value)
    
    print("\n  [Decision Prompt]")
    print(f"  {'Metric':<20} {'Old':>8} {'New':>8} {'Delta':>8}")
    print(f"  {'-'*44}")
    all_metrics = set()
    for v in metrics_by_prompt["decision"].values():
        all_metrics.update(v.keys())
    for m in sorted(all_metrics):
        old_vals = metrics_by_prompt["decision"]["old"].get(m, [])
        new_vals = metrics_by_prompt["decision"]["new"].get(m, [])
        old_pct = f"{sum(old_vals)/len(old_vals)*100:.0f}%" if old_vals else "N/A"
        new_pct = f"{sum(new_vals)/len(new_vals)*100:.0f}%" if new_vals else "N/A"
        delta = ""
        if old_vals and new_vals:
            d = (sum(new_vals) - sum(old_vals)) / len(old_vals) * 100
            delta = f"{d:+.0f}%"
        print(f"  {m:<20} {old_pct:>8} {new_pct:>8} {delta:>8}")
    
    print("\n  [Decompose Prompt]")
    print(f"  {'Metric':<20} {'Old':>8} {'New':>8} {'Delta':>8}")
    print(f"  {'-'*44}")
    all_metrics = set()
    for v in metrics_by_prompt["decompose"].values():
        all_metrics.update(v.keys())
    for m in sorted(all_metrics):
        old_vals = metrics_by_prompt["decompose"]["old"].get(m, [])
        new_vals = metrics_by_prompt["decompose"]["new"].get(m, [])
        old_pct = f"{sum(old_vals)/len(old_vals)*100:.0f}%" if old_vals else "N/A"
        new_pct = f"{sum(new_vals)/len(new_vals)*100:.0f}%" if new_vals else "N/A"
        delta = ""
        if old_vals and new_vals:
            d = (sum(new_vals) - sum(old_vals)) / len(old_vals) * 100
            delta = f"{d:+.0f}%"
        print(f"  {m:<20} {old_pct:>8} {new_pct:>8} {delta:>8}")
    
    print("\n  [Evaluate Prompt]")
    print(f"  {'Metric':<20} {'Old':>8} {'New':>8} {'Delta':>8}")
    print(f"  {'-'*44}")
    all_metrics = set()
    for v in metrics_by_prompt["evaluate"].values():
        all_metrics.update(v.keys())
    for m in sorted(all_metrics):
        old_vals = metrics_by_prompt["evaluate"]["old"].get(m, [])
        new_vals = metrics_by_prompt["evaluate"]["new"].get(m, [])
        old_pct = f"{sum(old_vals)/len(old_vals)*100:.0f}%" if old_vals else "N/A"
        new_pct = f"{sum(new_vals)/len(new_vals)*100:.0f}%" if new_vals else "N/A"
        delta = ""
        if old_vals and new_vals:
            d = (sum(new_vals) - sum(old_vals)) / len(old_vals) * 100
            delta = f"{d:+.0f}%"
        print(f"  {m:<20} {old_pct:>8} {new_pct:>8} {delta:>8}")
    
    # Save detailed results
    output_path = os.path.join(os.path.dirname(__file__), "ab_test_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Detailed results saved to: {output_path}")
    
    # Save summary report
    report_path = os.path.join(os.path.dirname(__file__), "ab_test_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"A/B Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Tasks: {len(TEST_TASKS)}\n")
        f.write(f"API: {API_BASE}\n\n")
        for r in results:
            f.write(f"\n{r['task']} ({r['complexity']})\n")
            f.write("-" * 40 + "\n")
            for prompt_type in ["decision", "decompose", "evaluate"]:
                for version in ["old", "new"]:
                    scores = r.get(prompt_type, {}).get(version, {}).get("scores", {})
                    f.write(f"  {prompt_type}/{version}: {scores}\n")
    print(f"  Summary report saved to: {report_path}")


if __name__ == "__main__":
    run_ab_test()
