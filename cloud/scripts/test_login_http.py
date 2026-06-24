"""快速测试登录HTTP接口"""
import urllib.request
import json

url = "http://127.0.0.1:8000/api/v1/auth/login"
data = json.dumps({
    "account": "admin@tt-tools.com",
    "password": "admin123",
    "device_fingerprint": "web"
}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
print(resp.read().decode())
