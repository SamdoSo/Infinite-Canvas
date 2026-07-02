# ============================================================
# Infinite-Canvas Docker 镜像打包导出脚本（Windows PowerShell）
# ============================================================
# 功能：
#   1. 读取 VERSION 文件作为镜像标签
#   2. 构建 Docker 镜像
#   3. 导出为 tar 文件（不压缩）
#   4. 将部署所需的文件复制到 deploy/ 目录
#
# 最终产物（deploy/ 目录）：
#   - infinite-canvas-<版本号>.tar     Docker 镜像文件
#   - docker-compose.yml                服务器部署用 compose 文件
#   - .env.example                      环境变量模板（请自行重命名为 .env 并填写）
#
# 服务器部署：
#   1. 将 deploy/ 下所有文件上传到服务器
#   2. docker load -i infinite-canvas-<版本号>.tar
#   3. cp .env.example .env 并填写配置
#   4. docker compose up -d
# ============================================================

# 错误时立即停止
$ErrorActionPreference = "Stop"

# 进入脚本所在目录（项目根目录）
Set-Location -Path $PSScriptRoot

# ---------- 读取版本号 ----------
if (-not (Test-Path "VERSION")) {
    Write-Error "未找到 VERSION 文件，请在项目根目录下运行本脚本。"
    exit 1
}
$VERSION = (Get-Content "VERSION" -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($VERSION)) {
    Write-Error "VERSION 文件为空。"
    exit 1
}

$IMAGE_NAME = "infinite-canvas"
$IMAGE_TAG = "${IMAGE_NAME}:${VERSION}"
$IMAGE_LATEST = "${IMAGE_NAME}:latest"
$TAR_FILE = "${IMAGE_NAME}-${VERSION}.tar"
$DEPLOY_DIR = "deploy"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Infinite-Canvas Docker 镜像打包导出" -ForegroundColor Cyan
Write-Host "  版本: $VERSION" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 检查 Docker ----------
Write-Host "[1/5] 检查 Docker 是否可用..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "  Docker 可用" -ForegroundColor Green
} catch {
    Write-Error "未检测到 Docker，请先安装并启动 Docker Desktop。"
    exit 1
}

# ---------- 2. 构建镜像 ----------
Write-Host ""
Write-Host "[2/5] 构建 Docker 镜像 ($IMAGE_TAG)..." -ForegroundColor Yellow
docker build -t $IMAGE_TAG -t $IMAGE_LATEST -f Dockerfile .
if ($LASTEXITCODE -ne 0) {
    Write-Error "镜像构建失败。"
    exit 1
}
Write-Host "  镜像构建成功" -ForegroundColor Green

# ---------- 3. 准备 deploy 目录 ----------
Write-Host ""
Write-Host "[3/5] 准备 deploy 目录..." -ForegroundColor Yellow
if (Test-Path $DEPLOY_DIR) {
    Remove-Item -Recurse -Force $DEPLOY_DIR
}
New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null
Write-Host "  已创建 deploy/ 目录" -ForegroundColor Green

# ---------- 4. 导出镜像 ----------
Write-Host ""
Write-Host "[4/5] 导出镜像为 tar 文件（可能需要几分钟）..." -ForegroundColor Yellow
$tarPath = Join-Path $DEPLOY_DIR $TAR_FILE

docker save -o $tarPath $IMAGE_TAG $IMAGE_LATEST
if ($LASTEXITCODE -ne 0) {
    Write-Error "镜像导出失败。"
    exit 1
}

$tarSize = [math]::Round((Get-Item $tarPath).Length / 1MB, 2)
Write-Host "  导出完成: ${TAR_FILE} (${tarSize} MB)" -ForegroundColor Green

# ---------- 5. 复制部署文件 ----------
Write-Host ""
Write-Host "[5/5] 复制部署所需文件..." -ForegroundColor Yellow

Copy-Item "docker-compose.deploy.yml" (Join-Path $DEPLOY_DIR "docker-compose.yml")
Write-Host "  - docker-compose.yml" -ForegroundColor Green

Copy-Item ".env.example" (Join-Path $DEPLOY_DIR ".env.example")
Write-Host "  - .env.example" -ForegroundColor Green

# ---------- 完成 ----------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  打包完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "产物位于: $(Join-Path $PSScriptRoot $DEPLOY_DIR)" -ForegroundColor White
Write-Host ""
Write-Host "服务器部署步骤：" -ForegroundColor Yellow
Write-Host "  1. 将 deploy/ 目录下所有文件上传到服务器"
Write-Host "  2. 加载镜像: docker load -i ${TAR_FILE}"
Write-Host "  3. 复制配置: cp .env.example .env  并按需填写"
Write-Host "  4. 启动服务: docker compose up -d"
Write-Host "  5. 访问: http://服务器IP:3000"
Write-Host ""
