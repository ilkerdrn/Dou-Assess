# DOU Assess 6.67 — Security Operations

## Evidence integrity scan

Administrators can use **Sistem & Güvenlik -> Kanıt bütünlüğü -> Bütünlük taraması çalıştır**.

API equivalent:

```http
POST /api/security/evidence-integrity/scan
```

Interpretation:

- `verified`: physical bytes match stored SHA-256.
- `mismatch`: physical bytes differ from the recorded evidence hash. Treat as an incident; do not replace the database hash to make the warning disappear.
- `missing`: database evidence record exists but its physical file is absent. Restore the exact file from a verified backup if available.

## Evaluator invitation

Create the workspace from the accreditation application. The UI displays the invitation URL only once. The token is carried in the URL fragment (`#token=...`), not a query string, and the public portal removes the fragment from browser history after reading it.

If an invitation is exposed or sent to the wrong recipient, revoke the workspace and issue a new workspace/token. Never copy the token into evidence descriptions, tickets or ordinary application logs.

## Controlled documents

Approval path:

1. Draft is prepared by the authenticated actor.
2. Draft is submitted.
3. A different authorized Quality/Admin actor reviews it.
4. Reviewed revision is approved by an authorized actor.

Do not bypass the workflow by editing database status fields directly.
