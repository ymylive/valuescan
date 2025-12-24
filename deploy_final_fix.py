import paramiko
import time

HOST = '82.158.88.34'
USER = 'root'
PASS = 'Qq159741'

def run_command(ssh, cmd, description):
    print(f"--- {description} ---")
    print(f"CMD: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            print(stdout.channel.recv(1024).decode(), end='')
        time.sleep(0.1)
    print(stdout.read().decode(), end='')
    err = stderr.read().decode()
    if err:
        print(f"\nSTDERR: {err}")

def upload_file(sftp, local_path, remote_path):
    print(f"Uploading {local_path} -> {remote_path}")
    sftp.put(local_path, remote_path)

def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS)
    sftp = ssh.open_sftp()
    
    project_dir = "/root/valuescan"

    # 1. Update Xray Listen Address (Allow Docker access)
    print("\n--- Updating Xray Listen Address ---")
    checker_script = f"{project_dir}/proxy_manager/node_checker.py"
    # Replace "listen": "127.0.0.1" with "listen": "0.0.0.0"
    run_command(ssh, f"sed -i 's\"listen\": \"127.0.0.1\"/\"listen\": \"0.0.0.0\"/g' {checker_script}", "Update node_checker.py")
    
    # Force config regeneration and restart
    # We need to run the checker once to regenerate config
    # We'll use the --switch flag which calls generate_xray_config
    # We need to ensure PROXY_SUBSCRIBE_URL is set
    env_cmd = "export PROXY_SUBSCRIBE_URL='https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469'"
    run_command(ssh, f"{env_cmd} && python3 {checker_script} --switch", "Regenerate Config via Switch")
    run_command(ssh, "systemctl restart xray", "Restart Xray")

    # 2. Update .env for Docker Proxy
    print("\n--- Updating .env for Docker Proxy ---")
    # Set proxy env vars for containers
    proxy_vars = {
        "ALL_PROXY": "socks5://host.docker.internal:1080",
        "HTTP_PROXY": "http://host.docker.internal:1080", # Xray usually supports HTTP on same port or we need socks5h
        # Wait, Xray inbound is SOCKS. curl/wget in containers often support socks5://
        # Go supports HTTP_PROXY=socks5://...
        # Let's stick to socks5
        "HTTPS_PROXY": "socks5://host.docker.internal:1080"
    }
    
    for key, value in proxy_vars.items():
        # Check if exists
        stdin, stdout, stderr = ssh.exec_command(f"grep '{key}=' {project_dir}/.env")
        if stdout.read().decode().strip():
            run_command(ssh, f"sed -i 's|^{key}=.*|{key}={value}|' {project_dir}/.env", f"Update {key}")
        else:
            run_command(ssh, f"echo '{key}={value}' >> {project_dir}/.env", f"Append {key}")

    # 3. Upload Code Updates
    print("\n--- Uploading Code ---")
    upload_file(sftp, "api/server.go", f"{project_dir}/api/server.go")
    upload_file(sftp, "web/src/components/HeaderBar.tsx", f"{project_dir}/web/src/components/HeaderBar.tsx")

    # 4. Rebuild
    print("\n--- Rebuilding Docker Containers ---")
    cmd = f"cd {project_dir} && nohup docker compose up -d --build > build_final.log 2>&1 &"
    ssh.exec_command(cmd)
    print("Build started in background. Check build_final.log for details.")

    sftp.close()
    ssh.close()

if __name__ == "__main__":
    main()
