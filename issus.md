Here's a detailed summary for your team:

---

## Issue Summary: SFTP Monitoring Logstash Pipeline Failure

### Problem Description

The SFTP monitoring Logstash pipeline (`sftp.conf`) started failing. The pipeline executes a Python script (`sftp.py`) that connects to `fts.hedgeserv.com` to perform upload/download tests for monitoring purposes.

### Evidence from Logstash Logs

The Logstash logs showed repeated JSON parse errors and timeout failures:

```
[2026-02-03T14:34:35,845][WARN ][logstash.codecs.jsonlines][sftp] JSON parse error, original data now in message field {:message=>"Unrecognized token 'args': was expecting ('true', 'false' or 'null')", :data=>"args: ['/usr/bin/sftp', 'sftpmonitor1@fts.hedgeserv.com']"}

[2026-02-03T14:34:35,846][WARN ][logstash.codecs.jsonlines][sftp] JSON parse error, original data now in message field {:data=>"buffer (last 100 chars): b'(yes/no)? '"}

[2026-02-03T14:34:37,812][WARN ][logstash.codecs.jsonlines][sftp] JSON parse error, original data now in message field {:data=>"after: <class 'pexpect.exceptions.TIMEOUT'>"}

[2026-02-03T14:39:20,144][WARN ][logstash.codecs.jsonlines][sftp] JSON parse error, original data now in message field {:data=>"Exception occured:  Timeout exceeded."}
```

The key indicator was:
```
buffer (last 100 chars): b'(yes/no)? '
before (last 100 chars): b':50:34:8d:4d:ca:05:be:c0:d3:69:d1:79:2a:3c.\r\nAre you sure you want to continue connecting (yes/no)? '
```

This showed the script was hanging at the SSH host key verification prompt.

### Troubleshooting Steps Performed

**Test 1: Running as root without `--test_connection` parameter**

```bash
python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx'
```

Result: Failed with timeout. The script defaulted to `--test_connection 'initial'` which expects the `(yes/no)?` prompt, but encountered a password prompt mismatch.

**Test 2: Running as root with `--test_connection 'regular'`**

```bash
python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx' --test_connection 'regular'
```

Result: **Success** — The script completed and output valid JSON:
```json
{"@timestamp": "2026-02-03T19:46:25.464949", "service": {"type": "SFTP", "name": "SFTPUpload"}, "log": {"level": "INFO"}, "hostname": "fts.hedgeserv.com", "event": {"type": "created"}}
{"@timestamp": "2026-02-03T19:46:25.465117", "service": {"type": "SFTP", "name": "SFTPDownload"}, "log": {"level": "INFO"}, "hostname": "fts.hedgeserv.com", "event": {"type": "sent"}}
```

**Test 3: Running as logstash user with `--test_connection 'regular'`**

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx' --test_connection 'regular'
```

Result: **Failed** with timeout:
```
Exception occured:  Timeout exceeded.
buffer (last 100 chars): b'(yes/no)? '
before (last 100 chars): b':50:34:8d:4d:ca:05:be:c0:d3:69:d1:79:2a:3c.\r\nAre you sure you want to continue connecting (yes/no)? '
```

This confirmed the issue was specific to the `logstash` user — the host key was not in the logstash user's known_hosts file.

**Test 4: Running as root user with `--test_connection 'regular'` (for comparison)**

```bash
runuser -u root -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx' --test_connection 'regular'
```

Result: **Success** — Confirmed the root user had the host key accepted.

---

## Root Cause

The SSH host key for `fts.hedgeserv.com` changed on the SFTP server. Each Linux user maintains their own `~/.ssh/known_hosts` file. The `root` user had previously accepted the new host key, but the `logstash` user had not.

When Logstash runs the SFTP monitoring script, it executes as the `logstash` user. Since the `logstash` user's known_hosts file did not contain the updated host key for `fts.hedgeserv.com`, SSH prompted for verification:

```
Are you sure you want to continue connecting (yes/no)?
```

Because the script runs non-interactively, it could not respond to this prompt and timed out after 30 seconds.

Possible reasons for the host key change:
- The SFTP server was rebuilt or reinstalled
- SSH was reconfigured or host keys were regenerated
- The server was migrated to new hardware
- The server was replaced with a new instance using the same hostname

---

## Solution

**Step 1:** Accept the new host key as the `logstash` user by running the script with `--test_connection 'initial'`:

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd '<password>' --test_connection 'initial'
```

**Step 2:** Verify the script works with regular connection mode:

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd '<password>' --test_connection 'regular'
```

**Step 3:** Confirm the Logstash pipeline is functioning correctly:

```bash
tail -f /var/log/logstash/logstash-plain.log | grep sftp
```

**Step 4:** Confirm with the team managing `fts.hedgeserv.com` that the host key change was intentional to rule out any security concerns.

---
