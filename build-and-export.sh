#!/usr/bin/env bash
# ============================================================
# Infinite-Canvas Docker 镜像打包导出脚本（Linux / macOS）
# ============================================================
# 功能：
#   1. 读取 VERSION 文件作为镜像标签
#   2. 构建 Docker 镜像
#   3. 导出为 tar.gz 压缩包
#   4. 将部署所需的文件复制到 deploy/ 目录
#
# 最终产物（deploy/ 目录）：
#   - infinite-canvas-<版本号>.tar.gz   Docker 镜像压缩包
#   - docker-compose.yml                服务器部署用 compose 文件
#   - .env.example                      环境变量模板（请自行重命名为 .env 并填写）
#
# 服务器部署：
#   1. 将 deploy/ 下所有文件上传到服务器
#   2. docker load -i infinite-canvas-<版本号>.tar.gz
#   3. cp .env.example .env 并填写配置
#   4. docker compose up -d
# ============================================================

set -euo pipefail

# 进入脚本所在目录（项目根目录）
cd "$(dirname "$0")"

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ---------- 读取版本号 ----------
if [ ! -f "VERSION" ]; then
    echo -e "${RED}未找到 VERSION 文件，请在项目根目录下运行本脚本。${NC}"
    exit 1
fi

VERSION=$(tr -d '[:space:]' < VERSION)
if [ -z "$VERSION" ]; then
    echo -e "${RED}VERSION 文件为空。${NC}"
    exit 1
fi

IMAGE_NAME="infinite-canvas"
IMAGE_TAG="${IMAGE_NAME}:${VERSION}"
IMAGE_LATEST="${IMAGE_NAME}:latest"
TAR_GZ_FILE="${IMAGE_NAME}-${VERSION}.tar.gz"
DEPLOY_DIR="deploy"

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Infinite-Canvas Docker 镜像打包导出${NC}"
echo -e "${CYAN}  版本: ${VERSION}${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ---------- 1. 检查 Docker ----------
echo -e "${YELLOW}[1/5] 检查 Docker 是否可用...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}未检测到 Docker，请先安装 Docker。${NC}"
    exit 1
fi
echo -e "${GREEN}  Docker 可用${NC}"

# ---------- 2. 构建镜像 ----------
echo ""
echo -e "${YELLOW}[2/5] 构建 Docker 镜像 (${IMAGE_TAG})...${NC}"
docker build -t "$IMAGE_TAG" -t "$IMAGE_LATEST" -f Dockerfile .
echo -e "${GREEN}  镜像构建成功${NC}"

# ---------- 3. 准备 deploy 目录 ----------
echo ""
echo -e "${YELLOW}[3/5] 准备 deploy 目录...${NC}"
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"
echo -e "${GREEN}  已创建 deploy/ 目录${NC}"

# ---------- 4. 导出镜像并压缩 ----------
echo ""
echo -e "${YELLOW}[4/5] 导出镜像并压缩为 tar.gz（可能需要几分钟）...${NC}"
docker save "$IMAGE_TAG" "$IMAGE_LATEST" | gzip > "${DEPLOY_DIR}/${TAR_GZ_FILE}"

GZ_SIZE=$(du -h "${DEPLOY_DIR}/${TAR_GZ_FILE}" | cut -f1)
echo -e "${GREEN}  导出完成: ${TAR_GZ_FILE} (${GZ_SIZE})${NC}"

# ---------- 5. 复制部署文件 ----------
echo ""
echo -e "${YELLOW}[5/5] 复制部署所需文件...${NC}"

cp docker-compose.deploy.yml "${DEPLOY_DIR}/docker-compose.yml"
echo -e "${GREEN}  - docker-compose.yml${NC}"

cp .env.example "${DEPLOY_DIR}/.env.example"
echo -e "${GREEN}  - .env.example${NC}"

# ---------- 完成 ----------
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  打包完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "产物位于: ${PWD}/${DEPLOY_DIR}"
echo ""
echo -e "${YELLOW}服务器部署步骤：${NC}"
echo "  1. 将 deploy/ 目录下所有文件上传到服务器"
echo "  2. 加载镜像: docker load -i ${TAR_GZ_FILE}"
echo "  3. 复制配置: cp .env.example .env  并按需填写"
echo "  4. 启动服务: docker compose up -d"
echo "  5. 访问: http://服务器IP:3000"
echo ""
