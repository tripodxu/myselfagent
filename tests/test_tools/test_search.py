import pytest
import os
import tempfile
from src.tools.search import SearchTool


class TestSearchTool:
    def setup_method(self):
        self.tool = SearchTool()
    
    def test_search_in_text(self):
        """"测试在文本中搜索"""
        text = "Hello World\nPython Programming\nHello Python"
        result = self.tool.execute(action="text", pattern="Hello", text=text)
        
        assert result["success"] is True
        assert result["total"] == 2
        assert result["matches"][0]["line_number"] == 1
        assert result["matches"][1]["line_number"] == 3
    
    def test_search_in_file(self):
        """"测试在文件中搜索"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("Line 1: Hello\nLine 2: World\nLine 3: Hello World")
            temp_file = f.name
        
        try:
            result = self.tool.execute(action="file", pattern="Hello", target=temp_file)
            
            assert result["success"] is True
            assert result["total"] == 2
        finally:
            os.unlink(temp_file)
    
    def test_search_no_results(self):
        """"测试无搜索结果"""
        text = "Hello World\nPython Programming"
        result = self.tool.execute(action="text", pattern="xyz", text=text)
        
        assert result["success"] is True
        assert result["total"] == 0
        assert len(result["matches"]) == 0
    
    def test_search_multiple_results(self):
        """"测试多个搜索结果"""
        text = "apple\nbanana\napple pie\ncherry\napple juice"
        result = self.tool.execute(action="text", pattern="apple", text=text)
        
        assert result["success"] is True
        assert result["total"] == 3
    
    def test_search_regex_pattern(self):
        """"测试正则表达式搜索"""
        text = "Email: test@example.com\nPhone: 123-456-7890"
        result = self.tool.execute(action="text", pattern=r"\d{3}-\d{3}-\d{4}", text=text)
        
        assert result["success"] is True
        assert result["total"] == 1
        assert "123-456-7890" in result["matches"][0]["content"]
    
    def test_search_case_insensitive(self):
        """"测试大小写不敏感搜索"""
        text = "Hello\nHELLO\nhello"
        result = self.tool.execute(action="text", pattern="hello", text=text)
        
        assert result["success"] is True
        assert result["total"] == 3
    
    def test_search_in_nonexistent_file(self):
        """"测试搜索不存在的文件"""
        result = self.tool.execute(action="file", pattern="test", target="/nonexistent/file.txt")
        
        assert result["success"] is False
        assert "不存在" in result["error"]
    
    def test_search_invalid_regex(self):
        """"测试无效的正则表达式"""
        text = "Hello World"
        result = self.tool.execute(action="text", pattern="[invalid", text=text)
        
        assert result["success"] is False
        assert "正则表达式错误" in result["error"]
    
    def test_search_unknown_action(self):
        """"测试未知搜索操作"""
        result = self.tool.execute(action="unknown", pattern="test")
        
        assert result["success"] is False
        assert "未知搜索操作" in result["error"]
    
    def test_search_in_files(self):
        """"测试在多个文件中搜索"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建测试文件
            with open(os.path.join(tmp_dir, "file1.txt"), "w", encoding="utf-8") as f:
                f.write("Hello World")
            with open(os.path.join(tmp_dir, "file2.txt"), "w", encoding="utf-8") as f:
                f.write("Python Hello")
            with open(os.path.join(tmp_dir, "file3.py"), "w", encoding="utf-8") as f:
                f.write("No match here")
            
            result = self.tool.execute(action="files", pattern="Hello", target=tmp_dir)
            
            assert result["success"] is True
            assert result["total_files"] == 2
    
    def test_search_in_files_with_extension_filter(self):
        """"测试按扩展名过滤搜索"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "file1.txt"), "w", encoding="utf-8") as f:
                f.write("Hello World")
            with open(os.path.join(tmp_dir, "file2.py"), "w", encoding="utf-8") as f:
                f.write("Hello Python")
            
            result = self.tool.execute(
                action="files",
                pattern="Hello",
                target=tmp_dir,
                extensions=[".txt"]
            )
            
            assert result["success"] is True
            assert result["total_files"] == 1
