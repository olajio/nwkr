# Deployment Status: cs01-nwkr-01

Date: January 26, 2026

## Summary
- Attempt 1: CredSSP TLS handshake failed during "Test connection"; metricbeat tasks did not run.
- Attempt 2: WinRM transport was NTLM and succeeded; HTTPS download failed with "Could not create SSL/TLS secure channel"; metricbeat not installed.

## Current State
- Metricbeat: Not installed
- WinRM connectivity: OK under NTLM
- Blocker: Host-side Schannel/TLS configuration and certificate trust for artifact endpoint.

## Next Actions
- Enable TLS 1.2 and strong crypto on Windows:
  - HKLM\SOFTWARE\Microsoft\.NETFramework\v4.0.30319 → SchUseStrongCrypto=1
  - HKLM\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319 → SchUseStrongCrypto=1 (if applicable)
- Ensure root/intermediate CA trust for the artifact host (e.g., Artifactory).
- Validate HTTPS connectivity locally with PowerShell:
  - Invoke-WebRequest https://<artifact-url> -UseBasicParsing
- Rerun Ansible playbook and confirm:
  - Download succeeds
  - Metricbeat service installed and running

## References
- Root Cause Analysis: ROOT_CAUSE_ANALYSIS.md
- Tracking Issue: https://github.com/olajio/nwkr/issues/1
- Logs: first_try.log (CredSSP handshake failure), nwkr.log (NTLM + HTTPS TLS failure)

Owner: Olamide Olajide (@olajio)
Status: In progress
