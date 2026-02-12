# ValuScan QuantRefactorV3 - 部署指南

**版本**: 3.0.0
**更新日期**: 2026-02-10

---

## 目录

1. [系统要求](#系统要求)
2. [部署前准备](#部署前准备)
3. [环境配置](#环境配置)
4. [后端部署](#后端部署)
5. [前端部署](#前端部署)
6. [数据库配置](#数据库配置)
7. [反向代理配置](#反向代理配置)
8. [系统服务配置](#系统服务配置)
9. [监控和日志](#监控和日志)
10. [故障排查](#故障排查)

---

## 系统要求

### 硬件要求
- **CPU**: 4核心或以上
- **内存**: 8GB RAM（推荐16GB）
- **存储**: 50GB可用空间
- **网络**: 稳定的互联网连接

### 软件要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Windows Server 2019+
- **Python**: 3.9+
- **Node.js**: 16+
- **Nginx**: 1.18+（可选，用于反向代理）
- **Git**: 2.25+

---

## 部署前准备

### 1. 检查清单

**必须完成**:
- [ ] 所有代码已提交到Git仓库
- [ ] 所有测试通过
- [ ] 环境变量已准备
- [ ] API密钥已生成（至少32字符）
- [ ] 数据库已创建（如需要）
- [ ] 防火墙规则已配置

**建议完成**:
- [ ] 备份现有系统（如有）
- [ ] 准备回滚计划
- [ ] 通知相关人员
- [ ] 准备监控工具

### 2. 获取代码

```bash
# 克隆仓库
git clone <repository-url> /opt/valuescan
cd /opt/valuescan

# 切换到生产分支
git checkout main

# 验证版本
git log -1
```

---

## 环境配置

### 1. 创建环境变量文件

创建 `.env` 文件：

```bash
# API密钥（必须，至少32字符）
VALUESCAN_API_KEY=your-secure-32-char-api-key-here

# AI服务配置
NOFX_AI_API_URL=https://api.openai.com/v1/chat/completions
NOFX_AI_API_KEY=your-openai-api-key
NOFX_AI_MODEL=gpt-4
NOFX_AI_MAX_TOKENS=8000
NOFX_AI_API_TIMEOUT=90

# 数据源配置
NOFX_PROXY=http://your-proxy:port  # 可选
COINGECKO_API_KEY=your-coingecko-key  # 可选
FRED_API_KEY=your-fred-api-key  # 可选

# 应用配置
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO

# 数据库配置（如需要）
DATABASE_URL=sqlite:///valuescan.db

# Telegram配置（如需要）
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```

### 2. 生成安全的API密钥

```bash
# Linux/Mac
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# 或使用openssl
openssl rand -base64 32
```

### 3. 设置文件权限

```bash
# 设置.env文件权限（仅所有者可读）
chmod 600 .env

# 设置应用目录权限
chown -R valuescan:valuescan /opt/valuescan
chmod -R 755 /opt/valuescan
```

---

## 后端部署

### 1. 安装Python依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r signal_monitor/requirements.txt

# 安装额外的生产依赖
pip install gunicorn Flask-Limiter
```

### 2. 验证安装

```bash
# 验证Python模块
python -c "import flask; import requests; import numpy; print('OK')"

# 验证配置
python -c "from api.config import init_config_api; print('OK')"
```

### 3. 初始化配置

```bash
# 创建配置文件（如不存在）
cp signal_monitor/config.example.py signal_monitor/config.py

# 编辑配置
nano signal_monitor/config.py
```

### 4. 运行后端服务

**开发模式**:
```bash
python api/server.py
```

**生产模式（使用Gunicorn）**:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 api.server:app \
  --timeout 120 \
  --access-logfile logs/access.log \
  --error-logfile logs/error.log \
  --log-level info
```

---

## 前端部署

### 1. 安装Node.js依赖

```bash
cd admin-web

# 安装依赖
npm install

# 或使用yarn
yarn install
```

### 2. 配置环境变量

创建 `admin-web/.env.production`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_TITLE=ValuScan Admin
```

### 3. 构建生产版本

```bash
# 构建
npm run build

# 验证构建
ls -lh dist/
```

### 4. 部署静态文件

**选项1: 使用Nginx**
```bash
# 复制构建文件到Nginx目录
sudo cp -r dist/* /var/www/valuescan-admin/

# 设置权限
sudo chown -R www-data:www-data /var/www/valuescan-admin/
```

**选项2: 使用Node.js服务器**
```bash
# 使用serve
npm install -g serve
serve -s dist -l 3001
```

---

## 数据库配置

### SQLite（默认）

```bash
# 创建数据目录
mkdir -p data

# 初始化数据库（如需要）
python -c "from database import init_db; init_db()"
```

### PostgreSQL（可选）

```bash
# 安装PostgreSQL客户端
pip install psycopg2-binary

# 创建数据库
createdb valuescan

# 更新.env
DATABASE_URL=postgresql://user:password@localhost/valuescan
```

---

## 反向代理配置

### Nginx配置

创建 `/etc/nginx/sites-available/valuescan`:

```nginx
# 后端API
upstream valuescan_backend {
    server 127.0.0.1:8000;
}

# 前端
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /var/www/valuescan-admin;
        try_files $uri $uri/ /index.html;
    }

    # API代理
    location /api/ {
        proxy_pass http://valuescan_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    # 日志
    access_log /var/log/nginx/valuescan-access.log;
    error_log /var/log/nginx/valuescan-error.log;
}
```

启用配置:
```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/valuescan /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### SSL配置（推荐）

```bash
# 使用Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 系统服务配置

### Systemd服务（Linux）

创建 `/etc/systemd/system/valuescan-backend.service`:

```ini
[Unit]
Description=ValuScan Backend Service
After=network.target

[Service]
Type=simple
User=valuescan
Group=valuescan
WorkingDirectory=/opt/valuescan
Environment="PATH=/opt/valuescan/venv/bin"
EnvironmentFile=/opt/valuescan/.env
ExecStart=/opt/valuescan/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 api.server:app --timeout 120
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务:
```bash
# 重新加载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start valuescan-backend

# 设置开机自启
sudo systemctl enable valuescan-backend

# 查看状态
sudo systemctl status valuescan-backend
```

### Windows服务

使用NSSM（Non-Sucking Service Manager）:

```powershell
# 下载NSSM
# https://nssm.cc/download

# 安装服务
nssm install ValuScanBackend "C:\opt\valuescan\venv\Scripts\python.exe" "C:\opt\valuescan\api\server.py"

# 配置服务
nssm set ValuScanBackend AppDirectory "C:\opt\valuescan"
nssm set ValuScanBackend AppEnvironmentExtra "VALUESCAN_API_KEY=your-key"

# 启动服务
nssm start ValuScanBackend
```

---

## 监控和日志

### 日志配置

创建日志目录:
```bash
mkdir -p logs
touch logs/access.log logs/error.log logs/app.log
```

配置日志轮转 `/etc/logrotate.d/valuescan`:
```
/opt/valuescan/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 valuescan valuescan
    sharedscripts
    postrotate
        systemctl reload valuescan-backend > /dev/null 2>&1 || true
    endscript
}
```

### 健康检查

```bash
# 检查后端健康
curl http://localhost:8000/api/health

# 检查前端
curl http://localhost:3001

# 检查认证
curl -H "X-API-Key: your-key" http://localhost:8000/api/config
```

### 监控脚本

创建 `scripts/monitor.sh`:
```bash
#!/bin/bash

# 检查后端服务
if ! systemctl is-active --quiet valuescan-backend; then
    echo "Backend service is down!"
    systemctl restart valuescan-backend
fi

# 检查API响应
if ! curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "API health check failed!"
fi

# 检查磁盘空间
DISK_USAGE=$(df -h /opt/valuescan | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "Disk usage is above 80%: ${DISK_USAGE}%"
fi
```

添加到crontab:
```bash
# 每5分钟检查一次
*/5 * * * * /opt/valuescan/scripts/monitor.sh >> /var/log/valuescan-monitor.log 2>&1
```

---

## 故障排查

### 常见问题

#### 1. 后端无法启动

**症状**: 服务启动失败或立即退出

**排查步骤**:
```bash
# 检查日志
tail -f logs/error.log

# 检查端口占用
netstat -tulpn | grep 8000

# 检查环境变量
env | grep VALUESCAN

# 手动运行查看错误
python api/server.py
```

**常见原因**:
- 端口被占用
- 环境变量未设置
- 依赖未安装
- 配置文件错误

#### 2. 认证失败

**症状**: 所有API请求返回401

**排查步骤**:
```bash
# 检查环境变量
echo $VALUESCAN_API_KEY

# 测试认证
curl -H "X-API-Key: your-key" http://localhost:8000/api/health

# 检查日志
grep "Unauthorized" logs/error.log
```

**解决方案**:
- 确认API密钥已设置
- 确认请求头格式正确
- 检查密钥是否匹配

#### 3. 前端无法连接后端

**症状**: 前端显示网络错误

**排查步骤**:
```bash
# 检查后端是否运行
curl http://localhost:8000/api/health

# 检查CORS配置
curl -H "Origin: http://localhost:3001" -I http://localhost:8000/api/health

# 检查Nginx配置
sudo nginx -t
```

**解决方案**:
- 确认后端正在运行
- 检查API_BASE_URL配置
- 检查Nginx代理配置
- 检查防火墙规则

#### 4. 内存使用过高

**症状**: 系统内存不足

**排查步骤**:
```bash
# 检查内存使用
free -h
ps aux --sort=-%mem | head -10

# 检查日志大小
du -sh logs/

# 检查缓存
du -sh /tmp/
```

**解决方案**:
- 减少Gunicorn worker数量
- 清理旧日志
- 优化缓存策略
- 增加系统内存

#### 5. API响应慢

**症状**: 请求超时或响应时间长

**排查步骤**:
```bash
# 测试响应时间
time curl http://localhost:8000/api/health

# 检查系统负载
top
htop

# 检查网络
ping api.openai.com
```

**解决方案**:
- 增加Gunicorn timeout
- 优化数据库查询
- 添加缓存
- 检查外部API响应时间

---

## 性能优化

### 1. Gunicorn配置优化

```bash
# 计算worker数量: (2 x CPU核心数) + 1
gunicorn -w 9 -b 0.0.0.0:8000 api.server:app \
  --worker-class=gthread \
  --threads=2 \
  --timeout=120 \
  --max-requests=1000 \
  --max-requests-jitter=50
```

### 2. Nginx缓存配置

```nginx
# 添加到nginx配置
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=valuescan_cache:10m max_size=100m;

location /api/health {
    proxy_pass http://valuescan_backend;
    proxy_cache valuescan_cache;
    proxy_cache_valid 200 1m;
}
```

### 3. 数据库优化

```python
# 添加索引（如使用PostgreSQL）
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_config_history_timestamp ON config_history(timestamp);
```

---

## 安全加固

### 1. 防火墙配置

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# 仅允许本地访问后端
sudo ufw deny 8000/tcp
```

### 2. 限制文件权限

```bash
# 限制敏感文件权限
chmod 600 .env
chmod 600 signal_monitor/config.py
chmod 700 scripts/
```

### 3. 定期更新

```bash
# 更新系统包
sudo apt update && sudo apt upgrade

# 更新Python依赖
pip list --outdated
pip install --upgrade <package>

# 更新Node.js依赖
npm outdated
npm update
```

---

## 备份和恢复

### 备份脚本

创建 `scripts/backup.sh`:
```bash
#!/bin/bash

BACKUP_DIR="/backup/valuescan"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env signal_monitor/config.py

# 备份数据库
cp data/valuescan.db $BACKUP_DIR/valuescan_$DATE.db

# 备份日志
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### 恢复步骤

```bash
# 停止服务
sudo systemctl stop valuescan-backend

# 恢复配置
tar -xzf /backup/valuescan/config_20260210_120000.tar.gz

# 恢复数据库
cp /backup/valuescan/valuescan_20260210_120000.db data/valuescan.db

# 启动服务
sudo systemctl start valuescan-backend
```

---

## 附录

### A. 端口列表

| 服务 | 端口 | 说明 |
|------|------|------|
| 后端API | 8000 | Gunicorn |
| 前端 | 3001 | 管理界面 |
| Nginx | 80/443 | 反向代理 |

### B. 目录结构

```
/opt/valuescan/
├── api/                    # API模块
├── signal_monitor/         # 核心监控逻辑
├── admin-web/             # 管理前端
├── logs/                  # 日志文件
├── data/                  # 数据文件
├── venv/                  # Python虚拟环境
├── .env                   # 环境变量
└── scripts/               # 部署脚本
```

### C. 环境变量完整列表

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| VALUESCAN_API_KEY | 是 | - | API认证密钥 |
| NOFX_AI_API_URL | 是 | - | AI服务URL |
| NOFX_AI_API_KEY | 是 | - | AI服务密钥 |
| NOFX_AI_MODEL | 否 | gpt-4 | AI模型 |
| NOFX_AI_MAX_TOKENS | 否 | 8000 | 最大token数 |
| NOFX_AI_API_TIMEOUT | 否 | 90 | API超时（秒）|
| FLASK_ENV | 否 | production | Flask环境 |
| LOG_LEVEL | 否 | INFO | 日志级别 |

---

**文档版本**: 1.0.0
**最后更新**: 2026-02-10
**维护者**: ValuScan Team
