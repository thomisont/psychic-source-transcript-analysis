# Phase 1 – Supabase Auth Implementation Plan

_Use this checklist to track progress implementing lightweight authentication for the internal "How Is Lily Doing" dashboard._

## Goal
Introduce a secure yet simple login flow for ~6 internal users, powered by Supabase Auth. All non‑auth routes become protected by `login_required`.

---

## Task Checklist

- [ ] **Supabase Auth Setup**
  - [ ] Enable Auth in Supabase project (Email provider)
  - [ ] Decide **invite‑only** _vs_ **domain allow‑list** (`psychicsource.com`)
  - [ ] Add the 5‑6 initial users (or invite them)
  - [ ] Obtain `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
  - [ ] Add keys to `.env` (dev) and secrets store (prod)

- [x] **Backend Integration**
  - [ ] Install `supabase-py` (`requirements.txt`)
  - [ ] Create `auth/supabase_auth.py` helper with:
    - `authenticate(email, password)`
    - `verify_jwt(token)` (JWKS caching)
  - [ ] Add `supabase_client` to `create_app()`
  - [ ] Implement `login_required` decorator or Flask‑Login wrapper
  - [ ] Protect all existing blueprints except `/login`, `/signup`, `/static/*`

- [x] **Auth Routes & Views**
  - [ ] `/login` (GET form ➜ POST authenticate ➜ set cookie ➜ redirect)
  - [ ] `/logout` (clears cookie, redirects to `/login`)
  - [ ] Optional `/signup` (if domain allow‑list)
  - [ ] Error handling + flash messages

- [x] **Front‑End Updates**
  - [ ] Create minimal login page (Bootstrap form, project branding)
  - [ ] Update navbar: show `{{ current_user.email }}` & "Log out"
  - [ ] Hide navbar/user menu on login page

- [ ] **Testing & QA**
  - [ ] Local dev "DEV_USER" auto‑login shortcut (controlled by ENV)
  - [ ] Unit tests for token verification & route protection
  - [ ] Manual QA: failed login, successful login, logout, cookie expiry
  - [ ] (Optional) Playwright / Cypress e2e smoke test

---

## Timing Estimate
| Task | Effort |
|------|--------|
| Supabase configuration | 0.5 day |
| Backend integration | 1 day |
| Routes & Views | 0.5 day |
| Front‑end tweaks | 0.5 day |
| Tests & QA | 0.5 day |
| **Total** | **~3 days** |

---

## References
- Supabase Auth Docs: https://supabase.com/docs/guides/auth
- Example Flask + Supabase Auth blog: https://dev.to/... (placeholder)
- JWT Best Practices (OWASP): https://cheatsheetseries.owasp.org/... (placeholder) 