import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASS = 'Qq159741'

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS)
    
    print("--- Listing conf.d ---")
    stdin, stdout, stderr = ssh.exec_command("ls -F /etc/nginx/conf.d/")
    print(stdout.read().decode())
    
    print("--- Reading nginx.conf ---")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/nginx.conf")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
