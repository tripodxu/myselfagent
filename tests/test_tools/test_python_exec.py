import pytest
from src.tools.python_exec import PythonExecTool


class TestPythonExecTool:
    def setup_method(self):
        self.tool = PythonExecTool(timeout=5)
    
    def test_exec_simple_code(self):
        """"测试执行简单Python代码"""
        result = self.tool.execute(code="print('Hello, World!')")
        assert result["success"] is True
        assert "Hello, World!" in result["output"]
    
    def test_exec_with_output(self):
        """"测试捕获输出"""
        code = "x = 5\ny = 10\nprint(f'Sum: {x + y}')"
        result = self.tool.execute(code=code)
        assert result["success"] is True
        assert "Sum: 15" in result["output"]
    
    def test_exec_with_error(self):
        """"测试错误处理"""
        code = "raise ValueError('Test error')"
        result = self.tool.execute(code=code)
        assert result["success"] is False
        assert "ValueError" in result["error"]
    
    def test_exec_timeout(self):
        """"测试执行超时"""
        code = "import time; time.sleep(10)"
        tool = PythonExecTool(timeout=1)
        result = tool.execute(code=code)
        assert result["success"] is False
        assert "超时" in result["error"]
    
    def test_exec_blocked_import_os(self):
        """"测试禁止导入os模块"""
        code = "import os; print(os.getcwd())"
        with pytest.raises(ImportError) as exc_info:
            self.tool.execute(code=code)
        assert "os" in str(exc_info.value)
    
    def test_exec_blocked_import_subprocess(self):
        """"测试禁止导入subprocess模块"""
        code = "import subprocess; subprocess.run(['ls'])"
        with pytest.raises(ImportError) as exc_info:
            self.tool.execute(code=code)
        assert "subprocess" in str(exc_info.value)
    
    def test_exec_allowed_imports(self):
        """"测试允许的导入"""
        code = "import math; print(math.pi)"
        result = self.tool.execute(code=code)
        assert result["success"] is True
        assert "3.14" in result["output"]
    
    def test_exec_multiline_code(self):
        """"测试多行代码"""
        code = """
def add(a, b):
    return a + b

result = add(3, 4)
print(f'Result: {result}')
"""
        result = self.tool.execute(code=code)
        assert result["success"] is True
        assert "Result: 7" in result["output"]
