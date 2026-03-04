# dashboard/

React + Tailwind admin UI. Build last.

## Purpose
Web interface for admins to manage skills (CRUD) and configure Locker. Connects to the
vault API and auth endpoints.

## Rules
- Build AFTER all backend APIs (vault, auth, proxy) are stable
- React + Tailwind
- Do NOT embed or cache raw skill content in the frontend bundle
- Admin login flow required — no anonymous access
