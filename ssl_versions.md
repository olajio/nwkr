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







The output is a bit garbled due to formatting, but here's what it's telling you:

## What This Means

| Protocol | Status |
|----------|--------|
| **SSL 2.0** | `DisabledByDefault=1` — **Disabled** (good, it's insecure) |
| **SSL 3.0** | No registry entry — using OS default (disabled on 2012 R2+) |
| **TLS 1.0** | No registry entry — using OS default (**enabled**) |
| **TLS 1.1** | No registry entry — using OS default (**enabled**) |
| **TLS 1.2** | No registry entry — using OS default (**enabled**) |

The only explicit registry setting on this server is for SSL 2.0, which is disabled. Everything else falls back to Windows defaults.

## For Windows Server 2012/2012 R2 Defaults:
- **SSL 2.0** — Disabled
- **SSL 3.0** — Disabled (post-POODLE patches)
- **TLS 1.0** — Enabled
- **TLS 1.1** — Enabled
- **TLS 1.2** — Enabled

## Quick Summary

Your server likely has **TLS 1.0, 1.1, and 1.2 enabled** with SSL disabled. This is typical for a Windows 2012 server.

If you need to verify TLS 1.2 is actually working (important for CredSSP), run:

```powershell
[Net.ServicePointManager]::SecurityProtocol
```

If it returns `Tls12` or `Tls, Tls11, Tls12`, you're good. If CredSSP is still failing on those two servers, the issue is likely on the CredSSP configuration side rather than TLS versions.






That's the problem. Your .NET framework is only configured to use **SSL 3.0 and TLS 1.0**, both of which are outdated and insecure. **TLS 1.2 is not enabled for .NET applications**, which is likely causing your CredSSP failures.

## The Issue

Even though the OS supports TLS 1.2, .NET applications (including WinRM/CredSSP) aren't using it. Many modern services require TLS 1.2 minimum.

## Fix It

**Option 1: Enable TLS 1.2 for the current PowerShell session (temporary)**

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
```

**Option 2: Enable TLS 1.2 system-wide for .NET (permanent fix)**

Run this in an elevated PowerShell to set the registry keys:

```powershell
# For .NET Framework 4.x
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord

# For .NET Framework 3.5 (if used)
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\.NETFramework\v2.0.50727' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
Set-ItemProperty -Path 'HKLM:\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v2.0.50727' -Name 'SchUseStrongCrypto' -Value 1 -Type DWord
```

**Reboot the server** after making these changes.

## Verify After Reboot

```powershell
[Net.ServicePointManager]::SecurityProtocol
```

You should now see `Tls, Tls11, Tls12` or just `Tls12`.

This should resolve the CredSSP handshake failures on es03-nwkrs-01 and es01-nwkr-01.

----
----
---
Determine the version of .NET Framework
---
Run this one-liner in PowerShell:

```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full' -Name Release, Version | Select-Object Version, Release
```

## Interpreting the Release Number

| Release Value | .NET Framework Version |
|---------------|------------------------|
| 378389 | 4.5 |
| 378675 | 4.5.1 (Win 8.1/Server 2012 R2) |
| 378758 | 4.5.1 |
| 379893 | 4.5.2 |
| 393295 | 4.6 (Win 10) |
| 393297 | 4.6 |
| 394254 | 4.6.1 (Win 10 Nov Update) |
| 394271 | 4.6.1 |
| 394802 | 4.6.2 (Win 10 Anniversary) |
| 394806 | 4.6.2 |
| 460798 | 4.7 (Win 10 Creators) |
| 460805 | 4.7 |
| 461308 | 4.7.1 (Win 10 Fall Creators) |
| 461310 | 4.7.1 |
| 461808 | 4.7.2 (Win 10 April 2018) |
| 461814 | 4.7.2 |
| 528040 | 4.8 (Win 10 May 2019) |
| 528049 | 4.8 |
| 533320+ | 4.8.1 |

**To check all installed .NET versions (including older 2.x/3.x):**

```powershell
Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP' -Recurse | Get-ItemProperty -Name Version -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '^(?!S)\p{L}'} | Select-Object PSChildName, Version
```
