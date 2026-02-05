# Troubleshooting SFTP Monitoring Logstash Pipeline Failure: SSH Host Key Verification Issue

## Overview

This article documents an issue where the SFTP monitoring Logstash pipeline was failing due to an SSH host key verification problem. The root cause was that the `logstash` user did not have the updated SSH host key for the SFTP server in its `known_hosts` file.

---

## Symptoms

The Logstash pipeline executing the SFTP monitoring Python script was failing with the following errors in the Logstash logs (`/var/log/logstash/logstash-plain.log`):

```
JSON parse errors: "Unrecognized token 'args': was expecting ('true', 'false' or 'null')"
Buffer content: b'(yes/no)? '
Timeout exceptions after 30 seconds
Before buffer: b':50:34:8d:4d:ca:05:be:c0:d3:69:d1:79:2a:3c.\r\nAre you sure you want to continue connecting (yes/no)? '
```

The key indicator was the `(yes/no)?` prompt in the buffer, which indicated SSH was prompting for host key verification.

---

## Background

The Logstash pipeline uses an `exec` input to run a Python script that connects to an SFTP server:

```ruby
exec {
    command => "python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd '${SFTP}' --test_connection 'regular'"
    interval => 280
    codec => "json_lines"
}
```

**Important:** Logstash runs as the `logstash` user, not as `root`. This means:

- The script executes under the `logstash` user context
- SSH looks for the `known_hosts` file in the `logstash` user's home directory
- Each Linux user maintains a separate `~/.ssh/known_hosts` file

---

## Root Cause Analysis

The SSH host key for `fts.hedgeserv.com` had changed on the SFTP server. While the `root` user had already accepted the new host key, the `logstash` user had not.

When Logstash ran the script as the `logstash` user, SSH prompted for host key verification:

```
Are you sure you want to continue connecting (yes/no)?
```

Since this is a non-interactive execution, the script could not respond to the prompt, causing a 30-second timeout and subsequent failure.

---

## Manual Testing and Diagnosis

### Testing as Root User (Successful)

Running the script as `root` worked because `root` already had the host key:

```bash
python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py \
  --hostname 'fts.hedgeserv.com' \
  --pwd 'xxxxxxxx' \
  --test_connection 'regular'
```

**Result:** Success - returned valid JSON output.

### Testing as Logstash User (Failed)

Running the script as the `logstash` user failed:

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py \
  --hostname 'fts.hedgeserv.com' \
  --pwd 'xxxxxxxx' \
  --test_connection 'regular'
```

**Result:** Failed - script hung waiting for host key verification prompt, then timed out.

This confirmed that the issue was user-specific and related to the `logstash` user's SSH configuration.

---

## Resolution

### Step 1: Identify the Logstash User's Home Directory

The `logstash` user's home directory may not be where you expect. Check it with:

```bash
grep logstash /etc/passwd
```

This returns the home directory path (6th field in the output).

### Step 2: Create the .ssh Directory and Add the Host Key

```bash
# Get the logstash user's home directory
LOGSTASH_HOME=$(grep logstash /etc/passwd | cut -d: -f6)
echo "Logstash home directory: $LOGSTASH_HOME"

# Create the .ssh directory if it doesn't exist
mkdir -p ${LOGSTASH_HOME}/.ssh

# Add the SFTP server's host key to known_hosts
ssh-keyscan fts.hedgeserv.com >> ${LOGSTASH_HOME}/.ssh/known_hosts
```

### Step 3: Set Correct Ownership and Permissions

```bash
# Set ownership to logstash user
chown -R logstash:logstash ${LOGSTASH_HOME}/.ssh

# Set secure permissions
chmod 700 ${LOGSTASH_HOME}/.ssh
chmod 644 ${LOGSTASH_HOME}/.ssh/known_hosts
```

### Step 4: Verify the Fix

Test the script as the `logstash` user:

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py \
  --hostname 'fts.hedgeserv.com' \
  --pwd 'xxxxxxxx' \
  --test_connection 'regular'
```

**Result:** Success - script returns valid JSON output without prompts.

### Step 5: Confirm Logstash Pipeline is Working

Monitor the Logstash logs to confirm the pipeline is functioning:

```bash
tail -f /var/log/logstash/logstash-plain.log | grep sftp
```

---

## Why Copying to /var/lib/logstash/.ssh/ Didn't Work

An initial attempt to copy the `known_hosts` file to `/var/lib/logstash/.ssh/` did not resolve the issue. This is because `/var/lib/logstash/` was **not** the `logstash` user's actual home directory as defined in `/etc/passwd`.

SSH specifically looks for the `known_hosts` file in the user's home directory as defined in `/etc/passwd`, not in any arbitrary directory. Always verify the actual home directory before making changes.

---

## Key Takeaways

1. **Logstash runs as the `logstash` user** - Any external commands executed via the `exec` input run under this user context, not as `root`.

2. **Each user has their own SSH known_hosts** - Host keys accepted by `root` are not automatically available to other users.

3. **Always verify the user's home directory** - Use `grep <username> /etc/passwd` to find the actual home directory before modifying SSH configuration.

4. **Test as the correct user** - Use `runuser -u <username> -- <command>` to test commands as a specific user.

5. **SSH host key changes require action** - When an SFTP/SSH server's host key changes, all users that connect to that server need to accept the new key.

---

## Prevention

To prevent this issue in the future:

1. **Coordinate host key changes** - When SFTP server host keys are changed, notify teams that have automated connections to those servers.

2. **Document service account SSH dependencies** - Maintain a list of service accounts (like `logstash`) that have SSH/SFTP connections and their target servers.

3. **Monitor for SSH errors** - Set up alerting for SSH-related errors in Logstash logs, such as "host key verification" or connection timeouts.

4. **Verify host key changes are intentional** - Always confirm with the server team that a host key change was planned and not a sign of a security incident.

---

## Commands Reference

| Action | Command |
|--------|---------|
| Find user's home directory | `grep logstash /etc/passwd` |
| Test script as logstash user | `runuser -u logstash -- python3 -W ignore /path/to/script.py` |
| Add host key to known_hosts | `ssh-keyscan <hostname> >> /path/to/.ssh/known_hosts` |
| Set directory permissions | `chmod 700 /path/to/.ssh` |
| Set file permissions | `chmod 644 /path/to/.ssh/known_hosts` |
| Set ownership | `chown -R logstash:logstash /path/to/.ssh` |
| Monitor Logstash logs | `tail -f /var/log/logstash/logstash-plain.log \| grep sftp` |

---

## Related Files and Paths

- Logstash config: `/etc/logstash/conf.d/sftp.conf`
- Python script: `/etc/logstash/scripts/sftp_monitoring/sftp.py`
- Logstash logs: `/var/log/logstash/logstash-plain.log`
- Logstash user home: Check with `grep logstash /etc/passwd`
