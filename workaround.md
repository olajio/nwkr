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
