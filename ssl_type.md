PS C:\Users\oolajide-a> 'SSL 2.0','SSL 3.0','TLS 1.0','TLS 1.1','TLS 1.2' | ForEach-Object { $p=$_; 'Client','Server' |
ForEach-Object { Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\$p\
$_" -ErrorAction SilentlyContinue | Select-Object @{n='Protocol';e={$p}}, @{n='Type';e={$_}}, Enabled, DisabledByDefault
 }}

Protocol                      Type                          Enabled                                   DisabledByDefault
--------                      ----                          -------                                   -----------------
SSL 2.0                       @{DisabledByDefault=1; PSP...                                                           1




[Net.ServicePointManager]::SecurityProtocol
Ssl3, Tls


---
---
PS C:\Users\oolajide-a> Get-ChildItem 'HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP' -Recurse | Get-ItemProperty -Na
me Version -ErrorAction SilentlyContinue | Where-Object { $_.PSChildName -match '^(?!S)\p{L}'} | Select-Object PSChildNa
me, Version

PSChildName                                                 Version
                                               
Client                                                      4.6.01055
Full                                                        4.6.01055
Client                                                      4.0.0.0



