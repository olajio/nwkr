Here's a one-liner to check SSL/TLS versions enabled on a Windows 2012 server:

```powershell
Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\*\Server' -ErrorAction SilentlyContinue | Select-Object PSChildName, Enabled, DisabledByDefault
```

If you want a more comprehensive check that shows both client and server settings for all protocols:

```powershell
'SSL 2.0','SSL 3.0','TLS 1.0','TLS 1.1','TLS 1.2' | ForEach-Object { $p=$_; 'Client','Server' | ForEach-Object { Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$p\$_" -ErrorAction SilentlyContinue | Select-Object @{n='Protocol';e={$p}}, @{n='Type';e={$_}}, Enabled, DisabledByDefault }}
```

**Note:** If the registry keys don't exist, it means the OS defaults are in use. For Windows Server 2012:
- TLS 1.0, 1.1, 1.2 enabled by default
- SSL 2.0, SSL 3.0 disabled by default

To quickly check what's actually negotiable (tests against a local port like WinRM 5986):

```powershell
[Net.ServicePointManager]::SecurityProtocol
```

This shows what .NET will use for outbound connections, which often reflects the system configuration.
