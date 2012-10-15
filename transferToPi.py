import argparse, os, sys, re, paramiko, string,time

conveyor_dir = "makerbot/conveyor/"
output_dir = conveyor_dir + "remote_obj_dir/"

raspi_ip = 'raspi ip goes here'
name = 'usergoesheere'
passwd = 'passgoeshere'

printtofile = False
use_gcodefile_start_end = True

print sys.argv
target_index = -1
for i, item in enumerate(sys.argv):
    if re.search('\.gcode', item):
        target_index = i
        break
else:
    raise Exception("Couldnt find a gcode argument")
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
    print target.name, new_name
    sys.argv[target_index] = new_name #fix path to remote

    print "COPYING DONE"

    print "EXECUTING PRINT REMOTELY"

    if not printtofile:
        cmd = 'cd ~/' + conveyor_dir + ';' + 'python conveyor_cmdline_client.py -c conveyor-dev.conf print ' + new_name + ' --skip-start-end'
    else:
        cmd = 'cd ~/' + conveyor_dir + ';' + 'python conveyor_cmdline_client.py -c conveyor-dev.conf printtofile ' + new_name + ' ' + string.replace(new_name, '.gcode', '.s3g')
    
    
    print cmd
    #cmd = 'cd ~/' + conveyor_dir + '; ls'
    stdin, stdout, stderr = ssh.exec_command(cmd)

    #while not stdout.channel.exit_status_ready():
      #  if stdout.recv_ready():
         #   print stdout.recv()
    stdout.channel.recv_exit_status()
    print stdout.readlines()
except Exception, e:
    print "ERROR"
    print "%s" % e
else:
    print "SUCCESS"
finally:
    ssh.close()
    print "QUIT"
