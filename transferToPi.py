import argparse, os, sys, re, paramiko, string

output_dir = "makerbot/conveyor/remote_obj_dir/"
raspi_ip = '192.168.1.121'
name = 'noah'
passwd = 'uwishuknewthis'

#passwd = 'uWishuknwthis'

print sys.argv
for i, item in enumerate(sys.argv):
    if re.search('\.gcode', item):
        target_index = i
print sys.argv

#Open File
target = open(sys.argv[target_index],'r')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(
    paramiko.AutoAddPolicy())
try:
    args = ' '.join(sys.argv[1::])
    print args
    ssh.connect(raspi_ip, username=name, password=passwd)
    print "SSH Connected"
    
    ftp = ssh.open_sftp()
    ftp.chdir(output_dir)
    ftp.put(target.name, os.path.basename(target.name))
    ftp.close()

    new_name = '~/' + output_dir + os.path.basename(target.name)
    sys.argv[target_index] = new_name #fix path to remote

    print "COPYING DONE"

    print "EXECUTING PRINT REMOTELY"
    cmd = 'python conveyor_cmdline_client.py -c conveyor-dev.conf printtofile ' + new_name + ' ' + string.replace(new_name, '.gcode', ',s3g')
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print stdout.readlines()
except Exception, e:
    print "ERROR"
    print "%s" % e
else:
    print "SUCESS"
finally:
    ssh.close()
    print "QUIT"
