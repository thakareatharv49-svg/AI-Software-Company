# Nexora HQ status endpoint

The optional `GET /api/hq/status` endpoint is a dedicated service-to-service interface for the parent-company dashboard.

## Configure

Set `NEXORA_HQ_STATUS_TOKEN` in the AI Software Developer server environment to a randomly generated secret containing at least 32 characters. Restart the server after changing it. If the token is not configured, the endpoint returns `503`; missing or incorrect bearer credentials receive `401`.

Nexora HQ must be configured independently with:
- `NEXORA_AI_SOFTWARE_DEVELOPER_URL`: the AI Software Developer base URL.
- `NEXORA_AI_SOFTWARE_DEVELOPER_TOKEN`: the same service token, stored only in the HQ server environment.

Use HTTPS outside local development. Do not commit real tokens or expose them in browser assets.

## Response

A successful response includes only:
- `service`: `ai-software-developer`
- `status`: `operational` or `degraded`
- `active_missions`, `queued_missions`, `completed_missions`, `blocked_missions`
- `updated_at`: UTC timestamp for the snapshot

The status is degraded when at least one mission is blocked or failed. Failed missions contribute to the degraded state but are not added to the blocked-mission count. Mission names, objectives, task details, repositories, and controls are intentionally excluded.

The endpoint is read-only. It does not start, stop, retry, create, publish, or mutate missions or products.
