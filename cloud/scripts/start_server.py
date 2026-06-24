"""启动开发服务器"""
import subprocess, os, sys
env = os.environ.copy()
env["PYTHONPATH"] = "d:\\TT Tools"
env["APP_HOST"] = "0.0.0.0"
env["APP_DATABASE_URL"] = "sqlite+aiosqlite:///d:/TT Tools/data/tt_tools.db"
python = "D:\\localPath\\venvs\\cloud-app-shell\\Scripts\\python.exe"
script = "d:\\TT Tools\\cloud\\app-shell\\main.py"
subprocess.run([python, script], env=env, cwd="d:\\TT Tools")
