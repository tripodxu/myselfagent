import pytest
import os
import tempfile
from src.tools.file_io import FileIOTool


class TestFileIOTool:
    def test_read_file(self):
        """"测试读取文件"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("Hello, World!")
            
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="read", path=test_file)
            
            assert result["success"] is True
            assert result["content"] == "Hello, World!"
    
    def test_write_file(self):
        """"测试写入文件"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "output.txt")
            
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="write", path=test_file, content="Test content")
            
            assert result["success"] is True
            with open(test_file, "r", encoding="utf-8") as f:
                assert f.read() == "Test content"
    
    def test_list_files(self):
        """"测试列出目录文件"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 创建测试文件
            with open(os.path.join(tmp_dir, "file1.txt"), "w") as f:
                f.write("file1")
            with open(os.path.join(tmp_dir, "file2.txt"), "w") as f:
                f.write("file2")
            os.makedirs(os.path.join(tmp_dir, "subdir"))
            
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="list", path=tmp_dir)
            
            assert result["success"] is True
            assert len(result["items"]) == 3
            
            names = [item["name"] for item in result["items"]]
            assert "file1.txt" in names
            assert "file2.txt" in names
            assert "subdir" in names
    
    def test_read_nonexistent_file(self):
        """"测试读取不存在的文件"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "nonexistent.txt")
            
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="read", path=test_file)
            
            assert result["success"] is False
            assert "不存在" in result["error"]
    
    def test_write_to_restricted_path(self):
        """"测试写入受限路径"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            safe_dir = os.path.join(tmp_dir, "safe")
            restricted_file = os.path.join(tmp_dir, "restricted", "file.txt")
            
            tool = FileIOTool(allowed_paths=[safe_dir])
            result = tool.execute(
                action="write",
                path=restricted_file,
                content="malicious"
            )
            
            assert result["success"] is False
            assert "不允许" in result["error"] or "权限" in result["error"]
    
    def test_read_restricted_path(self):
        """"测试读取受限路径"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            safe_dir = os.path.join(tmp_dir, "safe")
            restricted_file = os.path.join(tmp_dir, "restricted", "file.txt")
            
            tool = FileIOTool(allowed_paths=[safe_dir])
            result = tool.execute(action="read", path=restricted_file)
            
            assert result["success"] is False
            assert "不允许" in result["error"] or "权限" in result["error"]
    
    def test_unknown_action(self):
        """"测试未知操作"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="delete", path=os.path.join(tmp_dir, "test.txt"))
            
            assert result["success"] is False
            assert "未知操作" in result["error"]
    
    def test_write_creates_parent_directory(self):
        """"测试写入时自动创建父目录"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = os.path.join(tmp_dir, "subdir", "nested", "file.txt")
            
            tool = FileIOTool(allowed_paths=[tmp_dir])
            result = tool.execute(action="write", path=test_file, content="nested file")
            
            assert result["success"] is True
            with open(test_file, "r", encoding="utf-8") as f:
                assert f.read() == "nested file"
