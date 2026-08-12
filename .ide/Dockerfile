FROM python:3.11-slim

WORKDIR /app

# 安装依赖
RUN pip install --no-cache-dir flask requests

# 复制项目
COPY . .

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "app.py"]