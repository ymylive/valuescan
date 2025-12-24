import paramiko
import time

HOST = '82.158.88.34'
USER = 'root'
PASS = 'Qq159741'

def main():
    print(f"Connecting to {HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS)
    
    # Check Nginx config sites-enabled
    print("\n--- Listing Nginx Sites ---")
    stdin, stdout, stderr = ssh.exec_command("ls -F /etc/nginx/sites-enabled/")
    print(stdout.read().decode())
    
    # Read default or relevant config
    print("\n--- Reading Default Config ---")
    # Try generic names
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/sites-enabled/default 2>/dev/null || cat /etc/nginx/sites-enabled/valuescan 2>/dev/null")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()

