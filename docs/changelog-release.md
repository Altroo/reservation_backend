# Reservation release 3.16.0

This release adds a bilingual changelog (French: **Nouveautés**), safe update announcements and persistent light/dark mode. The initial 45 dated entries are reconstructed from 197 distinct reachable commits across the frontend and backend repositories. These are development dates, not verified production deployment dates. Full hashes, subjects, bodies, file lists and date classifications are in `changelog-history-sources.json`.

The numbering follows product milestones: reservations on 11 March 2026 (1.0.0), premises/rents on 30 March (2.0.0), residence management on 31 March (3.0.0). Capability dates increment minor; corrections, compatibility and documentation increment patch. The sixteen later capability dates lead to 3.16.0 on 9 October. Existing package metadata was 0.1.0 and neither repository had release tags.

## Deployment

1. Deploy backend, then apply migrations with `docker exec reservation_web python manage.py migrate --noinput`. The existing deployment hook rebuilds containers but does not run migrations.
2. Deploy frontend and verify `https://reservation.elbouazzatiholding.ma/api/app-version` returns 3.16.0 with `Cache-Control: no-store`.
3. Verify health and published bilingual changelog entries. The initial seed preserves administrator edits and does not announce a release.
4. Save the latest `WsMaintenanceState` through its normal model/admin save path, setting version 3.16.0 only after the matching frontend is healthy. Preserve any intentionally active maintenance state.
5. Check HTTP bootstrap and websocket announcements. Tabs running JavaScript from before this feature need one normal refresh; later updates prompt automatically and never force-reload unsaved work.

## Validation

Use `reservation_backend.settings_changelog_test` only with the dedicated local PostgreSQL instance on 127.0.0.1:55442, user `reservation_preview`, database `reservation_release_preview`. It overrides all application database settings, cache and channel layer. Historical migrations contain PostgreSQL-specific SQL, so SQLite is unsuitable. Preview users and reservations belong only to this isolated database.

Backend: full regression suite, focused changelog/websocket tests, `manage.py check`, and `makemigrations --check --dry-run`. Frontend: full Jest suite, TypeScript, ESLint and production build. Browser checks cover both languages and themes, staff/member navigation, mobile drawer, first/last history entries, error/retry, populated/empty charts, preference persistence, unsaved input, announcement dismissal, maintenance suppression and unavailable releases. A simulated old bundle was checked against the real availability endpoint; updating loaded the current bundle, preserved path/query/hash and removed the temporary marker.
