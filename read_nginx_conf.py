import paramiko

HOST = '82.158.88.34'
USER = 'root'
PASS = 'Qq159741'

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS)
    
    print("--- Reading cornna.qzz.io.conf ---")
    stdin, stdout, stderr = ssh.exec_command("cat /etc/nginx/conf.d/cornna.qzz.io.conf")
    print(stdout.read().decode())
    
    ssh.close()

if __name__ == "__main__":
    main()
