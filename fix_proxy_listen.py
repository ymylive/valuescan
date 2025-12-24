import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASS = 'Qq159741'

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS)
    
    print("--- Fixing node_checker.py ---")
    script_path = "/root/valuescan/proxy_manager/node_checker.py"
    
    # Read file
    ftp = ssh.open_sftp()
    with ftp.open(script_path, 'r') as f:
        content = f.read().decode('utf-8')
    
    # Replace
    new_content = content.replace('"listen": "127.0.0.1"', '"listen": "0.0.0.0"')
    
    # Write back
    with ftp.open(script_path, 'w') as f:
        f.write(new_content)
    
    ftp.close()
    
    print("--- Regenerating Config & Restarting ---")
    # We need to trigger config generation again. 
    # Just running --switch or --check might not save it if it thinks it's already current node?
    # --switch forces a switch which generates config.
    cmd = "export PROXY_SUBSCRIBE_URL='https://nano.nachoneko.cn/api/v1/client/subscribe?token=0564faff9cfd13442873e71f9a235469' && python3 /root/valuescan/proxy_manager/node_checker.py --switch"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode())
    
    stdin, stdout, stderr = ssh.exec_command("systemctl restart xray")
    print("Xray restarted.")
    
    ssh.close()

if __name__ == "__main__":
    main()
