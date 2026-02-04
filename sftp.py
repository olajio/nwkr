from datetime import datetime, timedelta
from argparse import ArgumentParser
import pathlib
import json
import time
import dateutil.parser
import pexpect # pip3 install pexpect

from pathlib import Path

import json_log_format as jlf

jlf.service_name = Path(__file__).stem
jlf.service_type = 'logstash_monitoring'
jlf.json_logging.init_non_web(custom_formatter=jlf.CustomJSONLog, enable_json=True)
logger = jlf.logging.getLogger(__name__)
logger.setLevel(jlf.logging.DEBUG)
logger.addHandler(jlf.logging.StreamHandler(jlf.sys.stdout))


parser = ArgumentParser(description='SFTP Test')
parser.add_argument('--hostname',required=True)
parser.add_argument('--pwd',required=True)
# parser.add_argument('--test_connection', choices=['initial','regular'], default='regular')
parser.add_argument('--test_connection', choices=['initial','regular'], default='initial')
args = parser.parse_args()

user = 'sftpmonitor1'
password = args.pwd
hostname = args.hostname


def main():
    start_time = datetime.now()
    time.sleep(1)
    mod_time = ''
    uploaded_flag = False
    try:
        mod_time = test_sftp()
    except Exception as e:
        print("Exception occured: ", str(e))

    if 'Elastic_test.zip' in mod_time:
        # We get the output from the commands and get the index of the 
        # 'ls -l Elastic_test.zip' command - 13(where the time is in the output) to calculate the time
        mod_time_index = mod_time.rindex('Elastic_test.zip') - 13
        mod_time_string = mod_time[mod_time_index:mod_time.rindex('Elastic_test.zip')]
        upload_time = dateutil.parser.parse(mod_time_string)
        # Add 59 seconds to make sure it will be more than the start time else we will see it as an ERROR
        # If it is not updated in the last minute we will see it as an error even with these 59 seconds
        upload_time = upload_time + timedelta(seconds=59)
        uploaded_flag = True

    test_file = 'Elastic_test.zip'

    time.sleep(1)
    
    last_download_time = pathlib.Path('/tmp/' + test_file).stat().st_mtime

    last_download_time = datetime.fromtimestamp(last_download_time)

    if last_download_time > start_time:
        log_level_out = 'INFO'
    else:
        log_level_out = 'ERROR'

    if uploaded_flag:
        log_level_upload = 'INFO' if upload_time >= start_time else 'ERROR'
    else:
        log_level_upload = 'ERROR'

    log_event('Upload', log_level_upload, hostname)
    log_event('Download', log_level_out, hostname)


def log_event(etype, log_level, hostname):
    service = {
        'type': 'SFTP',
        'name': 'SFTP' + etype
    }
    event_type = 'created' if etype == 'Upload' else 'sent'
    now = datetime.now().isoformat()
    log_event = {
        '@timestamp': now,
        'service': service,
        'log': {
            'level': log_level
        },
        'hostname': hostname,
        'event': {
            'type': event_type
        }
    }
    
    json_event = json.dumps(log_event)
    print(json_event)


def test_sftp():
    command = f"sftp {user}@{hostname}"
    # print("Here")

    child = pexpect.spawn(command)
    if args.test_connection == 'initial':
        child.expect_exact('(yes/no)? ')
        child.sendline('yes')

    child.expect_exact('password: ')
    child.sendline(password)

    child.expect_exact('sftp> ')
    child.sendline('cd Incoming/')
    # child.sendline('lpwd')
    child.sendline('lcd /etc/logstash/scripts/sftp_monitoring/')
    child.sendline('put Elastic_test.zip')
    child.sendline('lcd /tmp')
    child.sendline('get Elastic_test.zip')
    child.sendline('ls -l Elastic_test.zip')
    child.sendline('bye')
    modified_time = child.read()
    modified_time_string = str(modified_time, 'utf-8')

    return modified_time_string



if __name__=='__main__':
    try:
        main()
    
    except Exception as e:
        logger.error(f"There was an error executing logstash script - sftp.py. Error - {str(e)}")
