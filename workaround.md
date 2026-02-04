Running Logstash commands as root isn't straightforward because Logstash runs as the `logstash` user by default. Here are two workaround options:

---

**Option 1: Use sudo in the command (Recommended)**

Update the command in `sftp.conf` to use sudo:

```ruby
exec {
    command => "sudo /usr/bin/python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd '${SFTP}' --test_connection 'regular'"
    interval => 280
    codec => "json_lines"
}
```

Then allow the logstash user to run this command without a password by adding to `/etc/sudoers.d/logstash`:

```bash
echo 'logstash ALL=(root) NOPASSWD: /usr/bin/python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py *' > /etc/sudoers.d/logstash
chmod 440 /etc/sudoers.d/logstash
```

Restart Logstash:
```bash
systemctl restart logstash
```

---

**Option 2: Copy root's known_hosts to logstash user**

Instead of running as root, copy the host key from root to logstash:

```bash
mkdir -p /var/lib/logstash/.ssh
cp /root/.ssh/known_hosts /var/lib/logstash/.ssh/known_hosts
chown -R logstash:logstash /var/lib/logstash/.ssh
chmod 700 /var/lib/logstash/.ssh
chmod 644 /var/lib/logstash/.ssh/known_hosts
```

Then test as the logstash user:
```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx' --test_connection 'regular'
```

---

**Option 2 is cleaner** because it fixes the actual problem (missing host key) rather than changing privileges. Try that first.

---
---
Let's debug further. Check what's actually in the logstash user's known_hosts file and verify the home directory:

**Step 1: Check the logstash user's home directory**

```bash
grep logstash /etc/passwd
```

**Step 2: Check if the known_hosts file exists and has content**

```bash
cat /var/lib/logstash/.ssh/known_hosts
```

**Step 3: Check what SSH is looking for when running as logstash**

```bash
runuser -u logstash -- ssh -v -o BatchMode=yes sftpmonitor1@fts.hedgeserv.com 2>&1 | grep -i "known\|home\|Authenticity"
```

This will show which known_hosts file SSH is actually checking.

**Step 4: Try adding the host key directly as the logstash user**

```bash
runuser -u logstash -- ssh-keyscan fts.hedgeserv.com >> /var/lib/logstash/.ssh/known_hosts
```

**Step 5: Also check if logstash has a different home directory and add it there too**

```bash
# Get logstash home directory
LOGSTASH_HOME=$(grep logstash /etc/passwd | cut -d: -f6)
echo "Logstash home: $LOGSTASH_HOME"

# Create .ssh and add known_hosts there
mkdir -p ${LOGSTASH_HOME}/.ssh
ssh-keyscan fts.hedgeserv.com >> ${LOGSTASH_HOME}/.ssh/known_hosts
chown -R logstash:logstash ${LOGSTASH_HOME}/.ssh
chmod 700 ${LOGSTASH_HOME}/.ssh
chmod 644 ${LOGSTASH_HOME}/.ssh/known_hosts
```

Then test again:

```bash
runuser -u logstash -- python3 -W ignore /etc/logstash/scripts/sftp_monitoring/sftp.py --hostname 'fts.hedgeserv.com' --pwd 'xxxxxxxx' --test_connection 'regular'
```

What does Step 3 show you?
