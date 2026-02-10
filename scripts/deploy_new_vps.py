#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署到新VPS并清理旧VPS
"""
import sys
import os
import time
import tarfile
import tempfile
from pathlib import Path

try:
    import paramiko
except ImportError:
    print("请安装 paramiko: pip install paramiko")
    sys.exit(1)

# VPS配置
OLD_VPS = {
    "host": "43.128.227.29",
    "user": "root",
    "password": "Qq159741",
}

NEW_VPS = {
    "host": "43.133.12.98",
    "user": "root",
    "password": "Qq159741",
}

DOMAIN = "cornna.abrdns.com"
VPS_PATH = "/root/valuescan"
LOCAL_ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = [".git", ".github", ".idea", ".vscode", "__pycache__", "logs", "output",
             "data", "screenshots", "web/node_modules", "web/dist", "signal_monitor/output",
             "signal_monitor/chrome-debug-profile", "metacubexd", "valuescan_bak"]
SKIP_FILES = [".log", "nul", "valuescan-web-dist.tar.gz"]


def run_cmd(ssh, cmd, show=True):
    """执行SSH命令"""
    try:
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=600)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        if show:
            if out: print(out)
            if err and "WARNING" not in err: print(err, file=sys.stderr)
        return exit_code == 0, out, err
    except Exception as e:
        print(f"命令执行失败: {e}")
        return False, "", str(e)


def connect_ssh(config):
    """连接SSH"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(config["host"], 22, config["user"], config["password"], timeout=30)
    return ssh


def should_skip(path):
    """检查是否跳过"""
    path_str = path.as_posix()
    for d in SKIP_DIRS:
        if path_str == d or path_str.startswith(d + "/"):
            return True
    for f in SKIP_FILES:
        if path.name.endswith(f) or path.name == f:
            return True
    return False


def create_archive():
    """创建上传包"""
    temp_dir = Path(tempfile.mkdtemp())
    archive = temp_dir / "valuescan.tar.gz"

    with tarfile.open(archive, "w:gz") as tar:
        for base, dirs, files in os.walk(LOCAL_ROOT, topdown=True):
            base_path = Path(base)
            rel_base = base_path.relative_to(LOCAL_ROOT)

            if should_skip(rel_base):
                dirs[:] = []
                continue

            dirs[:] = [d for d in dirs if not should_skip(rel_base / d)]

            for f in files:
                rel_file = rel_base / f
                if not should_skip(rel_file):
                    tar.add(base_path / f, arcname=str(rel_file))

    return archive


def clean_old_vps():
    """清理旧VPS"""
    print("\n" + "="*50)
    print("  清理旧VPS: " + OLD_VPS["host"])
    print("="*50)

    try:
        ssh = connect_ssh(OLD_VPS)
        print("已连接旧VPS")

        # 停止服务
        run_cmd(ssh, "systemctl stop valuescan-api valuescan-monitor valuescan-token-refresher nginx 2>/dev/null || true")
        run_cmd(ssh, "systemctl disable valuescan-api valuescan-monitor valuescan-token-refresher 2>/dev/null || true")

        # 删除项目文件
        run_cmd(ssh, f"rm -rf {VPS_PATH}")
        run_cmd(ssh, "rm -rf /var/www/valuescan")
        run_cmd(ssh, "rm -f /etc/systemd/system/valuescan-*.service")
        run_cmd(ssh, "systemctl daemon-reload")

        print("旧VPS清理完成")
        ssh.close()
        return True
    except Exception as e:
        print(f"清理旧VPS失败: {e}")
        return False


def deploy_new_vps():
    """部署到新VPS"""
    print("\n" + "="*50)
    print("  部署到新VPS: " + NEW_VPS["host"])
    print("="*50)

    ssh = connect_ssh(NEW_VPS)
    print("已连接新VPS")

    # 1. 安装依赖
    print("\n[1/8] 安装系统依赖...")
    run_cmd(ssh, "apt-get update && apt-get install -y nginx python3-pip nodejs npm socat curl git")

    # 2. 上传代码
    print("\n[2/8] 上传代码...")
    archive = create_archive()
    remote_archive = f"/tmp/valuescan_{int(time.time())}.tar.gz"

    sftp = ssh.open_sftp()
    sftp.put(str(archive), remote_archive)
    sftp.close()

    run_cmd(ssh, f"mkdir -p {VPS_PATH}")
    run_cmd(ssh, f"tar -xzf {remote_archive} -C {VPS_PATH}")
    run_cmd(ssh, f"rm -f {remote_archive}")
    archive.unlink(missing_ok=True)

    # 3. 安装Python依赖
    print("\n[3/8] 安装Python依赖...")
    run_cmd(ssh, f"cd {VPS_PATH}/api && pip3 install -r requirements.txt")
    run_cmd(ssh, f"cd {VPS_PATH}/signal_monitor && pip3 install -r requirements.txt")

    # 4. 构建前端
    print("\n[4/8] 构建前端...")
    run_cmd(ssh, f"cd {VPS_PATH}/web && npm install && npm run build", show=False)
    run_cmd(ssh, f"mkdir -p /var/www/valuescan && cp -r {VPS_PATH}/web/dist/* /var/www/valuescan/")

    # 5. 安装acme.sh并申请证书
    print("\n[5/8] 申请SSL证书...")
    run_cmd(ssh, "curl https://get.acme.sh | sh -s email=admin@cornna.com", show=False)
    run_cmd(ssh, f"~/.acme.sh/acme.sh --issue -d {DOMAIN} --standalone --force", show=True)
    run_cmd(ssh, f"mkdir -p /etc/nginx/ssl")
    run_cmd(ssh, f"~/.acme.sh/acme.sh --install-cert -d {DOMAIN} --key-file /etc/nginx/ssl/{DOMAIN}.key --fullchain-file /etc/nginx/ssl/{DOMAIN}.crt --reloadcmd 'systemctl reload nginx'")

    # 6. 配置Nginx
    print("\n[6/8] 配置Nginx...")
    nginx_conf = f'''server {{
    listen 80;
    server_name {DOMAIN};
    return 301 https://$server_name$request_uri;
}}

server {{
    listen 443 ssl http2;
    server_name {DOMAIN};

    ssl_certificate /etc/nginx/ssl/{DOMAIN}.crt;
    ssl_certificate_key /etc/nginx/ssl/{DOMAIN}.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/valuescan;
    index index.html;

    location / {{
        try_files $uri $uri/ /index.html;
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
}}
'''
    run_cmd(ssh, f"cat > /etc/nginx/sites-available/valuescan << 'NGINX_EOF'\n{nginx_conf}\nNGINX_EOF")
    run_cmd(ssh, "ln -sf /etc/nginx/sites-available/valuescan /etc/nginx/sites-enabled/")
    run_cmd(ssh, "rm -f /etc/nginx/sites-enabled/default")
    run_cmd(ssh, "nginx -t && systemctl restart nginx")

    # 7. 配置systemd服务
    print("\n[7/8] 配置服务...")
    run_cmd(ssh, f"cp {VPS_PATH}/valuescan-api.service /etc/systemd/system/")
    run_cmd(ssh, f"cp {VPS_PATH}/valuescan-monitor.service /etc/systemd/system/")
    run_cmd(ssh, f"cp {VPS_PATH}/valuescan-token-refresher.service /etc/systemd/system/")
    run_cmd(ssh, "systemctl daemon-reload")
    run_cmd(ssh, "systemctl enable valuescan-api valuescan-monitor")

    # 8. 启动服务
    print("\n[8/8] 启动服务...")
    run_cmd(ssh, "systemctl restart valuescan-api valuescan-monitor")

    ssh.close()
    return True


def main():
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

    print("="*50)
    print("  ValueScan VPS 迁移部署")
    print("="*50)
    print(f"旧VPS: {OLD_VPS['host']} (将清理)")
    print(f"新VPS: {NEW_VPS['host']} (将部署)")
    print(f"域名: https://{DOMAIN}/")

    # 清理旧VPS
    clean_old_vps()

    # 部署新VPS
    if deploy_new_vps():
        print("\n" + "="*50)
        print("  部署完成!")
        print("="*50)
        print(f"\n访问地址: https://{DOMAIN}/")
        print(f"API地址: https://{DOMAIN}/api/")
    else:
        print("\n部署失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
