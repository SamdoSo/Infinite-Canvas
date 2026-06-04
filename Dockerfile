# 使用官方轻量级 Python 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，确保 Python 输出直接打印到控制台，不进行缓存
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 复制依赖声明文件
COPY requirements.txt .

# 安装依赖（默认使用阿里云镜像加速，方便国内用户快速构建；非国内用户可自行移除 -i 参数）
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 复制项目核心代码和静态资源
COPY main.py VERSION ./
COPY static/ ./static/
COPY workflows/ ./workflows/

# 声明容器对外暴露的端口
EXPOSE 3000

# 运行应用
CMD ["python", "main.py"]
