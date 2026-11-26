# DOU Assess 6.66.1 — Question Bank Runtime Hotfix

- Fixes `Soru Bankası > + Yeni soru oluştur` runtime binding.
- Removes dependency on legacy `question-bank-hotfix-6401.js?v=6.40.1`.
- Main `app.js` now owns the create action through delegated binding.
- Handles click-before-core-refresh by awaiting `refreshCore()` and refilling course options.
- Opens the editor before outcome refresh, so a slow outcome API cannot block the drawer.
- Cache-busts `app.js` as `6.66.1-question-bank-runtime-hotfix`.
- No database schema change.
- No design/UI redesign included.
- Regression: 229/229 PASS.
