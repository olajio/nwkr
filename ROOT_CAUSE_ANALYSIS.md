# Root Cause Analysis: Metricbeat Installation on cs01-nwkr-01

## Executive Summary

Two distinct failures occurred across the first and second AWS CodeBuild attempts targeting Windows host cs01-nwkr-01:

- Attempt 1 (first_try.log): WinRM authentication failed at the CredSSP TLS handshake during the "Test connection" task. No metricbeat tasks executed.
- Attempt 2 (nwkr.log): WinRM transport was NTLM (not CredSSP). Connection succeeded, but the metricbeat download via HTTPS failed with "Could not create SSL/TLS secure channel". Metricbeat did not install.

Outcome: Metricbeat was never installed on cs01-nwkr-01. The first failure was at the authentication layer (CredSSP TLS handshake). The second failure was at the application layer (HTTPS/TLS download) while using NTLM transport.

---

## Context and Problem Statement

The host cs01-nwkr-01 was targeted for metricbeat deployment. A hypothesis emerged that metricbeat may have been installed, removed, and then reinstalled. Analysis shows this did not happen:

- In Attempt 1, tasks never progressed past the connection test.
- In Attempt 2, tasks progressed but failed on the HTTPS download step; installation never completed.

---

## Attempt 1: CredSSP TLS Handshake Failure (Authentication Layer)

### Evidence
- Error: "Server did not respond with a CredSSP token after step TLS Handshake".
- Failure location: Ansible task "Test connection" (early in play).
- PLAY RECAP shows failure during connection; metricbeat tasks not reached.

### Interpretation
CredSSP requires a successful TLS handshake before credential exchange; the handshake did not complete. This blocked WinRM authentication entirely, causing all subsequent tasks to be skipped for this host.

### Likely Contributors
- TLS version mismatch (TLS 1.0/1.1 vs required TLS 1.2+).
- Host policy or Schannel configuration preventing handshake.
- Certificate trust or negotiation issues at transport layer.

---

## Attempt 2: NTLM Transport OK, HTTPS TLS Failure (Application Layer)

### Evidence
- Transport: `ansible_winrm_transport: ntlm` in nwkr.log (explicit NTLM usage).
- Connection test: OK; subsequent tasks executed.
- Download step (e.g., `win_get_url`) failed with: "The request was aborted: Could not create SSL/TLS secure channel".

### Interpretation
WinRM connectivity and authentication succeeded under NTLM. The failure occurred when downloading the metricbeat artifact over HTTPS, indicating host-side Schannel/TLS or certificate trust issues unrelated to WinRM transport.

### What Did and Did Not Happen
- Did: Connection succeeded; some tasks ran; a removal step may have executed as part of idempotent role logic.
- Did not: Successful HTTPS download; installation; service setup. Net effect: Metricbeat remains absent.

---

## Layered View of Failures

- Attempt 1: Transport/authentication layer failure (CredSSP TLS handshake).
- Attempt 2: Application/data transfer layer failure (HTTPS over Schannel TLS), while WinRM used NTLM successfully.

This distinction clarifies why Attempt 1 never reached install tasks, while Attempt 2 reached them but failed at artifact retrieval.

---

## Comparative Summary

| Aspect | Attempt 1 | Attempt 2 |
|--------|-----------|-----------|
| WinRM transport | CredSSP (attempted) | NTLM (explicit) |
| TLS handshake | Fails (no CredSSP token) | Succeeds for WinRM |
| Connection test | Failed | Passed |
| Install tasks | Not reached | Reached, download failed |
| Failure root | Auth/TLS handshake | HTTPS/TLS (Schannel) |
| Metricbeat result | Not installed | Not installed |

---

## Remediation Checklist (Attempt 2 focus)

- Windows Schannel/TLS:
  - Ensure TLS 1.2 is enabled system-wide.
  - Enable .NET strong crypto: `HKLM\SOFTWARE\Microsoft\.NETFramework\v4.0.30319` → `SchUseStrongCrypto=1`.
  - For WOW6432Node if applicable: `HKLM\SOFTWARE\Wow6432Node\Microsoft\.NETFramework\v4.0.30319` → `SchUseStrongCrypto=1`.
  - Confirm cipher suites include modern options compatible with server endpoint.

- Certificate trust:
  - Install/update root and intermediate CAs required by the artifact host (e.g., Artifactory).
  - Validate the endpoint certificate chain on the host using `certutil -verify` or manual inspection.

- Endpoint validation:
  - From cs01-nwkr-01, run PowerShell: `Invoke-WebRequest https://<artifact-url> -UseBasicParsing`.
  - If this fails with secure channel errors, the issue is host-side TLS/Schannel or trust.

- Ansible considerations:
  - Keep `ansible_winrm_transport: ntlm` if CredSSP is not required.
  - If CredSSP is needed in future, ensure host supports it (TLS 1.2+, CredSSP policies) and set `ansible_winrm_transport: credssp` accordingly.

---

## Optional Remediation (Attempt 1, if CredSSP desired)

- Verify WinRM listener over HTTPS is configured properly (if using 5986).
- Enforce TLS 1.2 in system TLS settings and policies.
- Confirm CredSSP is enabled and not restricted by local/security policies.
- Test with Ansible using `credssp` transport after enabling prerequisites.

---

## Verification Steps

1. Fix Schannel/TLS and certificate trust on cs01-nwkr-01.
2. Validate HTTPS download locally with PowerShell (`Invoke-WebRequest`).
3. Rerun Ansible playbook:
   - Connection: `ok` under NTLM.
   - Download: `changed` (artifact retrieved).
   - Install + service: `changed`/`ok`.
4. Confirm `metricbeat` Windows service is installed and running; metrics flow to Elasticsearch.

---

## Conclusion

- Attempt 1 failed at CredSSP TLS handshake (authentication); no install occurred.
- Attempt 2 used NTLM successfully; failed at HTTPS TLS (Schannel) during download; install did not occur.
- Addressing host-side TLS 1.2/strong crypto and certificate trust should resolve the download barrier and enable installation.

---

## Document Info

- Date: January 26, 2026
- Host: cs01-nwkr-01 (Windows)
- Service: Metricbeat
- Sources: first_try.log (CredSSP handshake failure), nwkr.log (NTLM + HTTPS TLS failure)
- Status: Updated with corrected transport distinction and remediation guidance.
