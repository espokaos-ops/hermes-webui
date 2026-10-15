# PR #8244 — evidencia local recuperada

Commit analizado: 9c1c9c532f406f534ce79fa023dbc5eb6ced4ba6

## Caché Pytest: /tmp/prmerge/.pytest_cache/v/cache/lastfailed
{
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_session_decode_failure_warns_with_state_dir_and_starts_fresh": true,
  "tests/test_issue2762_state_sync_profile_kwarg.py::test_get_state_db_honors_explicit_profile_kwarg": true,
  "tests/test_issue2762_state_sync_profile_kwarg.py::test_sync_session_usage_writes_only_to_named_profile": true,
  "tests/test_issue6892_sync_title_coverage.py::test_sync_session_title_persists_generated_title": true,
  "tests/test_webui_state_db_session_cwd.py::test_real_db_profile_none_updates_the_root_row_not_the_active_profile": true
}
## Caché Pytest: /tmp/pronly/.pytest_cache/v/cache/lastfailed
{
  "tests/test_async_delegation_webui_bridge.py::test_real_core_active_claim_survives_restart_and_retries_after_lease": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_expired_sessions_pruned_on_load": true,
  "tests/test_issue1499_onboarding_probe.py::TestIssue1499ProbeRouteEndToEnd::test_route_returns_dns_error_for_bad_host": true,
  "tests/test_issue7940_skill_stats_survive_profile_switch.py::test_changing_the_active_org_recounts_after_a_switch": true,
  "tests/test_managed_profile_startup.py::test_real_managed_bootstrap_preserves_named_profile_concurrency": true,
  "tests/test_tls_aware_probe.py::test_helper_self_signed_warns_and_succeeds": true,
  "tests/test_tls_aware_probe.py::test_helper_insecure_optin_is_silent": true
}
## Caché Pytest: /home/kaos/hermes-webui/.pytest_cache/v/cache/lastfailed
{
  "tests/test_issue7940_skill_stats_survive_profile_switch.py::test_changing_the_active_org_recounts_after_a_switch": true,
  "tests/test_managed_profile_startup.py::test_real_managed_bootstrap_preserves_named_profile_concurrency": true,
  "tests/test_async_delegation_webui_bridge.py::test_real_core_active_claim_survives_restart_and_retries_after_lease": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_expired_sessions_pruned_on_load": true,
  "tests/test_tls_aware_probe.py::test_helper_self_signed_warns_and_succeeds": true,
  "tests/test_tls_aware_probe.py::test_helper_insecure_optin_is_silent": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_session_decode_failure_warns_with_state_dir_and_starts_fresh": true,
  "tests/test_issue2762_state_sync_profile_kwarg.py::test_get_state_db_honors_explicit_profile_kwarg": true,
  "tests/test_issue2762_state_sync_profile_kwarg.py::test_sync_session_usage_writes_only_to_named_profile": true,
  "tests/test_issue6892_sync_title_coverage.py::test_sync_session_title_persists_generated_title": true,
  "tests/test_webui_state_db_session_cwd.py::test_real_db_profile_none_updates_the_root_row_not_the_active_profile": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_signing_key_read_failure_warns_with_state_dir": true,
  "tests/test_issue2762_state_sync_profile_kwarg.py::test_sync_session_usage_without_profile_kwarg_uses_active": true,
  "tests/test_issue2848_checkpoint_profile.py::test_checkpoint_save_completes_without_skill_lock": true,
  "tests/test_issue6964_title_dedup.py::test_sync_session_title_unique_titles_unchanged": true,
  "tests/test_webui_state_db_session_cwd.py::test_real_db_and_real_session_cache_survive_eviction_between_updates": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_session_read_failure_warns_with_state_dir_and_starts_fresh": true,
  "tests/test_auth_session_persistence.py::TestSessionPersistence::test_session_recursion_failure_warns_with_state_dir_and_starts_fresh": true,
  "tests/test_issue6892_sync_title_coverage.py::test_sync_session_title_does_not_overwrite_manual_rename": true,
  "tests/test_issue6892_sync_title_coverage.py::test_sync_session_title_preserves_existing_source_on_ensure": true,
  "tests/test_issue6964_title_dedup.py::test_sync_session_title_dedups_second_session_on_collision": true,
  "tests/test_issue6964_title_dedup.py::test_sync_session_title_dedup_retry_never_clobbers_manual_rename": true
}

## Informe de pruebas disponible
# Resultados de pruebas — PR #8244 (rama final `9c1c9c53` sobre `81036995`)

Leyenda: [OFICIAL] = `./scripts/test.sh` del repo con Python 3.11–3.13
aislado. [DIRECTO] = ejecución de funciones de test con stdlib (solo
cuando el runner era imposible). Entorno: `.venv` gestionado por el
runner; `HERMES_WEBUI_TEST_PYTHON=/tmp/py{311,312,313}/bin/python3`
(CPython standalone en /tmp, sin cambios al sistema).

## [OFICIAL] Tests de logs/timeout/i18n (los 4 ficheros afectados + vecino)
- `HERMES_WEBUI_TEST_PYTHON=/tmp/py312/python/bin/python3 ./scripts/test.sh -q tests/test_logs_ui_static.py tests/test_api_timeout.py tests/test_logs_endpoint.py tests/test_issue2098_logs_i18n.py`
  → **33 passed** (incluye `test_logs_poll_ordering_with_deferred_promises`,
  `test_logs_endpoint_window_without_newline_drops_fragment`,
  result-checks de severidad, checks endurecidos sin comentarios).
- Misma batería con `/tmp/py311/...` → **33 passed**.
- Misma batería con `/tmp/py313/...` → **33 passed**.
- Sobre rama final + master `81036995`, más los 2 tests nuevos de master:
  `... tests/test_issue8212_subpath_next_open_redirect.py tests/test_webui_gateway_chat_backend.py`
  → **96 passed**.

## [OFICIAL] Shards CI (`--shard-id=N --num-shards=5`, Python 3.12)
- shard 0/1/2/3/4: 5/7/2/3/6 failed, resto passed; **0 fallos en tests de logs
  en los 5 shards**. Repetición shard 2: mismos 2 (deterministas).
- Shard 0 sobre rama final + master nuevo: 4242 passed, mismos 5.

## [OFICIAL] Suite completa sin shardizar (referencia)
- `20421 passed, 333 skipped, 22 failed` (19m30s). Desglose evidenciado:
  7 idénticos sin estos cambios (árbol PR-puro `/tmp/pronly`); 1 anulado
  quitando proxies solo para ese comando (20/20 en su fichero);
  15 dependen del particionado y pasan aislados/agrupados. Ninguno en
  código de logs.

## [OFICIAL] Gates de lint
- `python3 -m compileall -q api server.py bootstrap.py mcp_server.py tests scripts` → exit 0 (solo SyntaxWarnings preexistentes en tests ajenos).
- `node --check static/panels.js static/workspace.js` → OK.
- `npx eslint --no-config-lookup -c eslint.runtime-guard.config.mjs "static/**/*.js"` (eslint@10, comando exacto CI) → exit 0.
- `scripts/scope_undef_gate.py` → exit 0 (su sonda eslint interna hace skip benigno).
- `ruff check` en los 5 .py tocados → set idéntico de diagnósticos antes/después (15 preexistentes, 0 en regiones del cambio).

## [DIRECTO] Capturas (no son tests)
- 8 PNG en `shot-*.png`, verificados visualmente uno por uno + `file(1)`.
- Metodología: servidores reales (PR-only :8792, final :8791), datos
  `synthetic-shot`, Chromium headless + Playwright; fallos/carga por
  intercepción de red. Scripts en `/tmp/shots/` (fuera del paquete).
