# Réservation AI Assistant

Status: locally tested, disabled by default pending shared-model acceptance. Application identifier: `reservation`. This adapter uses the centralized Chat AI Assistant package and the existing shared Colibri model.

## Installation and rollback

Install the existing requirements and vendored shared wheel. Preserve a private database restore file using the established deployment procedure, then run `python manage.py migrate chat_ai` and `python manage.py sync_ai_knowledge`. The additive migration creates assistant tables only. Existing startup does not migrate automatically.

Keep `CHAT_AI_ASSISTANT_ENABLED=False` until shared-model acceptance and activation authorization. Configure the existing internal inference URL, model identifier and key through private runtime settings. Do not publish credentials or expose raw inference. Defaults: 120-second model timeout,512 output tokens,30-day history retention. Disable the feature flag to roll back; retain tables and confirmed-action audit history. Never remove database volumes or reverse business writes as a source rollback.

Schedule `python manage.py purge_ai_history` with existing operations tooling. Expired conversations/pending actions and old read audits are removed; confirmed-action audit metadata remains. `sync_ai_knowledge` incrementally versions ten approved bilingual workflow documents.

## Native permissions and API

Every `/api/ai/v1/` request uses native JWT and an active authenticated user. Ordinary resources and annual metrics require native read access; Hilton reports use their independent flag, including Hilton-only users; accounts/settings require staff. Create/edit/delete navigation and bounded mutation proposals respect native flags. No company model or tab exists here. The application partition is internal; the API rejects supplied user/company/scope fields. History is user-owned and revalidates permissions/references on delivery and replay.

Endpoints provide capabilities, conversation create/list/detail/delete, JSON or authenticated SSE messages, record selection, exact confirmation and feedback. The seven tools are `search_records`, `get_record`, `navigate`, `financial_summary`, `knowledge`, `previous_results`, `prepare_change`. No shell, SQL, generic database or PDF tool exists. Hilton printing remains on its native authorized screen.

Eight resources: reservations, residences, apartments, costs, commercial premises, recorded rents, saved Hilton reports and staff user accounts. Search validates supported filters and pagination; combinations preserve AND semantics. Navigation uses allowlisted native routes; apartments resolve their residence and rents their premises. The model cannot invent destinations.

Annual financial metrics reuse native dashboard/balance/local services. Reservation amounts follow arrival year; returned/not-returned amounts include Airbnb/Bank only; paid rents follow rental year and mean recorded paid rents, not accounting profit. Monthly/arbitrary-date metrics and all-source collected cash are unsupported. Hilton retrieval reads stored reports without preview or recalculation writes. Unrecorded rent dues are not fabricated as records.

Supported edits: reservation guest/notes, residence/apartment name, cost description, premises name/address/tenant/notes and rent notes. Supported deletion refuses dependent residences/apartments/premises. Every write uses an owned five-minute exact-target confirmation, locks, fresh permission/dependency/fingerprint validation and native PUT/DELETE views. Full PUT rejects normalization of unrequested fields. Native history and assistant audit attribute the action to its instructing user. Financial values, dates, payment/status flags, relationships, accounts/permissions, Hilton writes and bulk operations are unsupported.

## Verification and limitations

Isolated PostgreSQL suite: 514 passed, including 43 assistant cases. Concurrent confirmations execute once; consumed or purged confirmations cannot repeat actions. Frontend: 26 assistant tests, TypeScript, lint and build pass. Real dummy-login browser checks use native data/APIs, including read-only denial, safe routes/list return, native confirmed deletion and actor history, owned chat history, multilingual greetings and the shared responsive light/dark interface. No company selector is added.

Synthetic datasets are prepared centrally, but Réservation model fine-tuning, held-out accuracy and server performance have not run. Application tests and deterministic shortcuts do not establish model accuracy. All application stages use one shared model and server-only serial training. Keep production activation disabled until required acceptance and approval.
