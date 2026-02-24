# Epic #25: Data Backup & Archiving — Refined User Stories

> **Generated:** 2026-02-24  
> **Scope:** Remaining work only — excludes already-implemented functionality  
> **Total Revised Estimate:** 9 SP (down from 13 SP original)

---

## Dependency Graph

```
US-10.1 (Automated DB Backups)
    └──▶ US-10.4 (DR Runbook) — needs backup procedures documented
US-10.2 (File Storage Backup)
    └──▶ US-10.4 (DR Runbook) — needs storage recovery procedures
US-10.3 (Design Archival)
    └── independent, but follows `archive_old_audit_logs` pattern
US-10.4 (DR Runbook)
    └── depends on US-10.1 and US-10.2 being finalized
```

**Recommended execution order:** US-10.1 → US-10.3 → US-10.2 → US-10.4

---

## Story #87 — US-10.1: Automated Database Backups

### What Already Exists
- `BackupService` class in `backend/app/services/backup.py` (full CRUD: create, restore, verify, list, cleanup)
- `DatabaseBackup` class in `backend/app/core/backup.py` (pg_dump, gzip, S3 upload, retention)
- `backup_database` Celery task in `backend/app/worker/tasks/maintenance.py` (lines 531–558)
- `verify_backups` Celery task (weekly, registered in beat schedule)
- `backup-database` entry in Celery beat schedule at `86400.0` (daily) in `backend/app/worker/celery.py`
- CloudNativePG `ScheduledBackup` at 2 AM daily in `k8s/base/cloudnative-pg/scheduled-backup.yaml`
- Commented-out Celery tasks at bottom of `backend/app/services/backup.py` (lines 600–659) — **not registered, not used**

### Refined User Story

**As a** platform operator,  
**I want** database backups to run on a reliable schedule with failure alerting and verified test coverage,  
**So that** I can trust the backup pipeline works end-to-end and be notified immediately if it fails.

### Remaining Work

The `backup_database` task **is registered** in Celery beat and `__init__.py`. The commented-out tasks in `backup.py` are dead code from an earlier approach. The actual gaps are:

1. **No tests for actual backup operations** — only enum/dataclass serialization tested
2. **No failure alerting** — backup failures are logged but not surfaced
3. **Weekly full backup task missing** — only daily `backup_database` (calls `db_backup.create_backup("full")`)
4. **Dead code cleanup** — commented-out Celery tasks in `services/backup.py` should be removed

### Acceptance Criteria

```gherkin
Feature: Automated Database Backups
  Background:
    Given the Celery worker is running
    And the maintenance queue is consuming tasks

  Scenario: Daily database backup completes successfully
    When the "backup_database" Celery beat task fires
    Then a pg_dump backup is created with gzip compression
    And the backup is uploaded to object storage under "backups/" prefix
    And old backups beyond 30-day retention are cleaned up
    And the task returns metadata including filename and size_bytes

  Scenario: Weekly full backup runs on Sunday
    When the "weekly_full_backup" Celery beat task fires on Sunday at 3 AM
    Then a full backup (database + files) is created via BackupService
    And the backup record is stored in the backup index

  Scenario: Backup failure triggers alert logging
    Given pg_dump is unavailable or database is unreachable
    When the "backup_database" task fires
    Then the task raises an exception
    And failure details are logged at ERROR level with structured fields
    And a "backup.failed" metric is emitted for Prometheus

  Scenario: Backup service tests cover real operations
    Given the test suite runs with mocked subprocess and storage
    When pytest executes test_backup_service.py
    Then BackupService.create_backup() is tested for DATABASE, FILES, FULL, INCREMENTAL types
    And BackupService.verify_backup() is tested for valid and corrupted backups
    And BackupService.restore_backup() is tested for success and not-found cases
    And BackupService.cleanup_old_backups() is tested for retention policy
    And BackupService.list_backups() is tested with type/status filters
    And DatabaseBackup.create_backup() is tested for full, schema, data types
    And all subprocess calls (pg_dump) are mocked, not executed

  Scenario: Dead code is removed
    Given the commented-out Celery tasks at the bottom of services/backup.py
    When the cleanup is applied
    Then lines 595-659 of services/backup.py are removed
    And no commented-out task definitions remain in the file
```

### Task Breakdown

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1 | Add `weekly_full_backup` Celery task | `backend/app/worker/tasks/maintenance.py` | New `@shared_task` calling `BackupService().create_backup(BackupType.FULL)`, modeled on existing `backup_database` task |
| 2 | Register weekly task in beat schedule | `backend/app/worker/celery.py` | Add `"weekly-full-backup"` entry: `schedule: crontab(hour=3, minute=0, day_of_week='sunday')` via `604800.0` or crontab |
| 3 | Export weekly task from `__init__.py` | `backend/app/worker/tasks/__init__.py` | Add `weekly_full_backup` to imports and `__all__` |
| 4 | Add Prometheus metrics on backup outcomes | `backend/app/worker/tasks/maintenance.py` | Add counter: `backup_operations_total{type, status}` — increment on success/failure in `backup_database` and `weekly_full_backup` |
| 5 | Write real BackupService integration tests | `backend/tests/services/test_backup_service.py` (new file) | Mock `asyncio.create_subprocess_exec`, `storage_client`, filesystem. Test `create_backup`, `verify_backup`, `restore_backup`, `cleanup_old_backups`, `list_backups`, `delete_backup` |
| 6 | Write DatabaseBackup unit tests | `backend/tests/core/test_backup.py` (new file) | Mock subprocess + storage_client. Test `create_backup`, `restore_backup`, `cleanup_old_backups`, `list_backups` |
| 7 | Write Celery task unit tests | `backend/tests/worker/test_backup_tasks.py` (new file) | Test `backup_database` and `weekly_full_backup` tasks with mocked services |
| 8 | Remove dead code | `backend/app/services/backup.py` | Delete commented-out Celery task block (lines ~595–659) |

### Revised Estimate: 3 SP

**Rationale:** Core backup infrastructure exists and is registered. Work is primarily testing (high volume but low complexity), a second scheduled task, metrics, and dead code removal.

### Testing Requirements
- **New file:** `backend/tests/services/test_backup_service.py` — ≥15 test cases covering `BackupService` methods
- **New file:** `backend/tests/core/test_backup.py` — ≥8 test cases covering `DatabaseBackup` and `DataExporter`
- **New file:** `backend/tests/worker/test_backup_tasks.py` — ≥4 test cases for task functions
- **Existing file:** `backend/tests/services/test_backup.py` — keep as-is (enum/dataclass tests are valid)
- All tests must mock `asyncio.create_subprocess_exec`, `storage_client`, and filesystem I/O
- Target: ≥90% line coverage on `services/backup.py` and `core/backup.py`

---

## Story #88 — US-10.2: File Storage Backup & Replication

### What Already Exists
- `BackupService._backup_files()` creates tar.gz of local file storage and uploads to S3
- `StorageBucket.ARCHIVES` exists in `backend/app/core/storage.py`
- `StorageClient` with full S3 API (upload, download, list, delete, copy) in `core/storage.py`
- MinIO is deployed via Helm with PVC persistence
- Manual backup/restore SOPs documented in `helm/STORAGE_IMPLEMENTATION.md`
- `data-engineering.md` specifies "Cross-region replication: Continuous" as target

### Refined User Story

**As a** platform operator,  
**I want** MinIO bucket versioning and lifecycle policies configured via infrastructure-as-code, with an automated replication health check,  
**So that** file storage is protected against accidental deletion and has a clear cold-storage transition.

### Remaining Work

1. **No bucket versioning** enabled on any MinIO bucket
2. **No lifecycle policies** (transition to cold tier, expiration)
3. **No replication automation** — manual SOPs only
4. **No replication health-check task**

### Acceptance Criteria

```gherkin
Feature: File Storage Backup & Replication
  Scenario: Bucket versioning is enabled on critical buckets
    Given MinIO is deployed via Helm
    When the initialization job runs
    Then versioning is enabled on "designs", "uploads", and "exports" buckets
    And version history is retained for 90 days

  Scenario: Lifecycle policies transition old data to cold storage
    Given lifecycle policies are configured on the "designs" bucket
    When a design file has not been accessed for 180 days
    Then it is transitioned to the ARCHIVES bucket (cold storage tier)
    And the transition is logged

  Scenario: Lifecycle policies expire temporary files
    Given lifecycle policies are configured on the "temp" bucket
    When a temp file is older than 7 days
    Then it is automatically deleted by the lifecycle rule

  Scenario: Storage replication health check runs weekly
    Given the "check_storage_replication" Celery task is scheduled
    When the task fires
    Then it verifies bucket versioning is enabled on critical buckets
    And it checks that recent files exist in both primary and archive locations
    And it logs results and emits a "storage.replication_check" metric

  Scenario: MinIO initialization script is idempotent
    When the MinIO init job runs multiple times
    Then no errors occur
    And versioning remains enabled
    And lifecycle policies are not duplicated
```

### Task Breakdown

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1 | Create MinIO init script with versioning + lifecycle | `backend/app/core/storage_init.py` (new) | Use boto3 `put_bucket_versioning` on designs/uploads/exports; `put_bucket_lifecycle_configuration` for temp (7d expiry) and designs (180d transition to archives) |
| 2 | Add Helm job for MinIO initialization | `helm/ai-part-designer/templates/minio-init-job.yaml` (new or extend existing) | K8s Job that runs `storage_init.py` on deploy |
| 3 | Add `check_storage_health` Celery task | `backend/app/worker/tasks/maintenance.py` | Weekly task: verify versioning enabled, check file counts in critical buckets, emit Prometheus gauge |
| 4 | Register task in beat schedule | `backend/app/worker/celery.py` | Add `"check-storage-health"` with `604800.0` schedule |
| 5 | Export from `__init__.py` | `backend/app/worker/tasks/__init__.py` | Add `check_storage_health` |
| 6 | Write tests for storage init | `backend/tests/core/test_storage_init.py` (new) | Mock boto3 calls, test idempotency, verify correct API calls |
| 7 | Write tests for health check task | `backend/tests/worker/test_storage_health.py` (new) | Mock storage client, test healthy and degraded scenarios |
| 8 | Update data-engineering.md | `docs/architecture/data-engineering.md` | Document bucket versioning and lifecycle policies in Section 4 (Object Storage) |

### Dependencies
- None (independent of other stories, but must complete before US-10.4)

### Revised Estimate: 2 SP

**Rationale:** `StorageClient` already wraps boto3. The work is configuration scripting (versioning/lifecycle API calls), a health-check task, and tests. No complex logic — primarily infrastructure glue.

### Testing Requirements
- **New file:** `backend/tests/core/test_storage_init.py` — ≥6 test cases (versioning enable, lifecycle create, idempotency, error handling)
- **New file:** `backend/tests/worker/test_storage_health.py` — ≥4 test cases (healthy, degraded, versioning disabled, empty bucket)
- All tests mock boto3/storage_client — no real MinIO calls

---

## Story #86 — US-10.3: Design Archival to Cold Storage

### What Already Exists
- `Design.status` supports `"archived"` value (defined in model comment, line 121)
- `SoftDeleteMixin` on Design model (has `deleted_at`)
- `archive_old_audit_logs` task in `maintenance.py` — complete pattern to follow (query old records → serialize to JSON → gzip → upload to ARCHIVES bucket → delete from DB)
- `StorageBucket.ARCHIVES` exists
- `StorageClient.copy_file()` method exists for cross-bucket operations
- No `archived_at` timestamp column on Design model
- No `archive_location` column on Design model
- No archive Celery task for designs
- No admin API endpoints for archive management

### Refined User Story

**As a** platform operator,  
**I want** designs inactive for >365 days to be automatically archived to cold storage with their files, and an admin API to manage archives,  
**So that** active database size stays manageable while archived designs remain retrievable.

### Acceptance Criteria

```gherkin
Feature: Design Archival to Cold Storage
  Scenario: Alembic migration adds archive columns to designs table
    When the migration runs
    Then the "designs" table has a new nullable "archived_at" TIMESTAMP WITH TIME ZONE column
    And the "designs" table has a new nullable "archive_location" VARCHAR(500) column
    And an index exists on "archived_at" for WHERE archived_at IS NOT NULL

  Scenario: Designs inactive for >365 days are auto-archived
    Given a design with status "ready" and updated_at older than 365 days
    And the design has no activity (no version changes, no shares, no views) in 365 days
    When the "archive_old_designs" Celery task fires (weekly)
    Then the design's CAD files are copied from "designs" bucket to "archives" bucket
    And the design metadata is serialized to JSON, gzipped, and stored in "archives"
    And the design's status is set to "archived"
    And the design's archived_at is set to current UTC timestamp
    And the design's archive_location is set to the archives bucket key
    And an audit log entry is created with action "design.archived"

  Scenario: Recently active designs are not archived
    Given a design with updated_at older than 365 days
    But the design was viewed within the last 365 days
    When the "archive_old_designs" task fires
    Then the design is NOT archived

  Scenario: Admin can list archived designs
    Given I am authenticated as an admin user
    When I send GET /api/v1/admin/archives/designs?page=1&per_page=20
    Then I receive a paginated list of archived designs
    And each entry includes id, name, archived_at, archive_location, original_size_bytes

  Scenario: Admin can restore an archived design
    Given I am authenticated as an admin user
    And a design exists with status "archived"
    When I send POST /api/v1/admin/archives/designs/{design_id}/restore
    Then the design's files are copied from "archives" back to "designs" bucket
    And the design's status is set to "ready"
    And archived_at and archive_location are cleared
    And an audit log entry is created with action "design.restored"

  Scenario: Admin can permanently delete an archived design
    Given I am authenticated as an admin user
    And a design exists with status "archived"
    When I send DELETE /api/v1/admin/archives/designs/{design_id}
    Then the archived files are deleted from the "archives" bucket
    And the design record is hard-deleted from the database
    And an audit log entry is created with action "design.permanently_deleted"

  Scenario: Non-admin users cannot access archive endpoints
    Given I am authenticated as a regular user
    When I send GET /api/v1/admin/archives/designs
    Then I receive 403 Forbidden

  Scenario: Archive configuration is configurable
    Given the setting DESIGN_ARCHIVE_AFTER_DAYS defaults to 365
    When the setting is changed to 180
    Then designs inactive for >180 days are eligible for archival
```

### Task Breakdown

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1 | Add `archived_at` and `archive_location` columns | `backend/app/models/design.py` | Add `archived_at: Mapped[datetime \| None]` (DateTime TZ) and `archive_location: Mapped[str \| None]` (String 500). Add partial index on `archived_at`. |
| 2 | Create Alembic migration | `backend/alembic/versions/xxxx_add_design_archive_columns.py` (new) | `op.add_column("designs", ...)` for both columns + index |
| 3 | Add `DESIGN_ARCHIVE_AFTER_DAYS` config | `backend/app/core/config.py` | `DESIGN_ARCHIVE_AFTER_DAYS: int = Field(default=365, ...)` |
| 4 | Create `DesignArchiveService` | `backend/app/services/design_archive.py` (new) | Methods: `archive_design()`, `restore_design()`, `delete_archived_design()`, `list_archived_designs()`, `find_archivable_designs()`. Follow patterns from `archive_old_audit_logs`. |
| 5 | Add `archive_old_designs` Celery task | `backend/app/worker/tasks/maintenance.py` | Weekly task calling `DesignArchiveService.find_archivable_designs()` then `archive_design()` for each. Pattern matches `archive_old_audit_logs`. |
| 6 | Register task in beat schedule | `backend/app/worker/celery.py` | Add `"archive-old-designs"` with `604800.0` schedule |
| 7 | Export from `__init__.py` | `backend/app/worker/tasks/__init__.py` | Add `archive_old_designs` |
| 8 | Create admin archive Pydantic schemas | `backend/app/schemas/archive.py` (new) | `ArchivedDesignResponse`, `ArchivedDesignListResponse`, `RestoreDesignResponse` |
| 9 | Create admin archive API endpoints | `backend/app/api/v1/archives.py` (new) | `GET /admin/archives/designs`, `POST /admin/archives/designs/{id}/restore`, `DELETE /admin/archives/designs/{id}`. Require admin role via `Depends(get_current_admin_user)`. |
| 10 | Register archive routes | `backend/app/api/v1/__init__.py` | Include archive router with prefix `/admin/archives` |
| 11 | Write DesignArchiveService tests | `backend/tests/services/test_design_archive.py` (new) | Test archive, restore, delete, list, find_archivable with mocked DB + storage |
| 12 | Write archive API endpoint tests | `backend/tests/api/test_archives.py` (new) | Test all endpoints, auth (admin-only), 404 cases, pagination |
| 13 | Write archive Celery task tests | `backend/tests/worker/test_archive_tasks.py` (new) | Test `archive_old_designs` with mocked service |

### Dependencies
- None (can start in parallel with US-10.1)

### Revised Estimate: 3 SP

**Rationale:** The `archive_old_audit_logs` task provides a complete pattern to follow. The Design model change is minor (2 columns + migration). The admin endpoints are straightforward CRUD. The bulk of the work is the service class and comprehensive tests.

### Testing Requirements
- **New file:** `backend/tests/services/test_design_archive.py` — ≥12 test cases
  - `test_archive_design_copies_files_to_archives_bucket`
  - `test_archive_design_sets_status_and_timestamps`
  - `test_archive_design_creates_audit_log`
  - `test_archive_design_with_missing_files_handles_gracefully`
  - `test_restore_design_copies_files_back`
  - `test_restore_design_clears_archive_fields`
  - `test_restore_design_not_found_raises_404`
  - `test_restore_non_archived_design_raises_error`
  - `test_delete_archived_design_removes_files_and_record`
  - `test_list_archived_designs_with_pagination`
  - `test_find_archivable_designs_respects_age_threshold`
  - `test_find_archivable_designs_excludes_recently_viewed`
- **New file:** `backend/tests/api/test_archives.py` — ≥8 test cases
  - `test_list_archives_requires_admin`
  - `test_list_archives_returns_paginated_results`
  - `test_restore_archive_success`
  - `test_restore_archive_not_found`
  - `test_delete_archive_success`
  - `test_regular_user_gets_403`
  - `test_restore_non_archived_design_returns_400`
  - `test_list_archives_empty_returns_empty_list`
- **New file:** `backend/tests/worker/test_archive_tasks.py` — ≥3 test cases

---

## Story #89 — US-10.4: Disaster Recovery Runbook

### What Already Exists
- DR fragments scattered across:
  - `docs/architecture/data-engineering.md` §7 (RTO/RPO table, backup strategy, recovery commands)
  - `helm/INGRESS_RUNBOOK.md` §Disaster Recovery (ingress/cert recovery)
  - `docs/operations/secrets-management.md` §Disaster Recovery (secrets rotation during DR)
  - `helm/STORAGE_IMPLEMENTATION.md` (MinIO PVC backup note)
  - `k8s/base/cloudnative-pg/README.md` (CloudNativePG recovery procedures)
- RTO/RPO defined: DB corruption 2h/24h, accidental deletion 1h/15m, full disaster 4h/24h
- No unified runbook
- No end-to-end DR test plan
- No communication/escalation procedures

### Refined User Story

**As a** platform operator,  
**I want** a single unified disaster recovery runbook with step-by-step procedures, a quarterly DR test plan, and an escalation matrix,  
**So that** any on-call engineer can execute recovery procedures without prior tribal knowledge.

### Acceptance Criteria

```gherkin
Feature: Disaster Recovery Runbook
  Scenario: Unified DR runbook exists
    Given DR procedures are currently scattered across 5+ documents
    When the runbook is created
    Then a single file docs/operations/disaster-recovery-runbook.md exists
    And it consolidates all DR procedures from existing docs
    And it does NOT duplicate content — it references source docs where appropriate

  Scenario: Runbook covers all failure scenarios
    Given the unified runbook
    Then it contains sections for:
      | Section | Content |
      | Overview | RTO/RPO targets table (from data-engineering.md) |
      | Prerequisites | Required access, tools, credentials references |
      | Database Recovery | CloudNativePG restore, pg_dump restore, PITR |
      | Object Storage Recovery | MinIO restore from backup, versioning rollback |
      | Application Recovery | Pod restart, rollback Helm release |
      | Ingress/TLS Recovery | Reference to helm/INGRESS_RUNBOOK.md |
      | Secrets Recovery | Reference to docs/operations/secrets-management.md |
      | Full Disaster | End-to-end recovery sequence with ordering |
      | Verification | Post-recovery health checks checklist |
      | Communication | Escalation matrix and notification templates |

  Scenario: Escalation matrix is defined
    Given the runbook
    Then it contains an escalation matrix with:
      | Severity | Response Time | Escalation Path |
      | P1 - Full Outage | 15 min | On-call → Tech Lead → VP Eng |
      | P2 - Partial Outage | 30 min | On-call → Tech Lead |
      | P3 - Degraded | 2 hours | On-call |

  Scenario: Quarterly DR test plan exists
    Given the runbook
    Then it contains a DR test plan section with:
      | Test | Frequency | Procedure |
      | Database restore from backup | Quarterly | Restore latest backup to staging |
      | Object storage recovery | Quarterly | Test versioning rollback |
      | Full failover simulation | Annually | Full rebuild from scratch |
    And each test has pass/fail criteria
    And a test log template is provided

  Scenario: Runbook is linked from existing docs
    When the runbook is published
    Then data-engineering.md §7 references the runbook
    And helm/INGRESS_RUNBOOK.md references the unified runbook
    And a link is added to docs/operations/ index if one exists
```

### Task Breakdown

| # | Task | File(s) | Details |
|---|------|---------|---------|
| 1 | Create unified DR runbook | `docs/operations/disaster-recovery-runbook.md` (new) | Consolidate procedures from 5+ sources. Include: overview, prerequisites, per-component recovery (DB, storage, app, ingress, secrets), full disaster sequence, verification, escalation, communication templates, DR test plan. |
| 2 | Add DR test plan section | Same file | Quarterly test procedures with pass/fail criteria and test log template |
| 3 | Add escalation matrix | Same file | Severity levels, response times, escalation paths, contact roles |
| 4 | Add communication templates | Same file | Incident notification template (Slack/email), status update template, post-mortem template |
| 5 | Cross-reference from data-engineering.md | `docs/architecture/data-engineering.md` | Add link to unified runbook in §7 |
| 6 | Cross-reference from INGRESS_RUNBOOK.md | `helm/INGRESS_RUNBOOK.md` | Add reference to unified runbook in DR section |
| 7 | Peer review by ops team | N/A | Runbook must be reviewed by ≥1 ops engineer for accuracy |

### Dependencies
- **Soft dependency on US-10.1 and US-10.2** — backup procedures should be finalized first so the runbook references accurate task names and processes
- Can start the runbook skeleton in parallel, then finalize after US-10.1/US-10.2

### Revised Estimate: 1 SP

**Rationale:** This is purely documentation. All the technical content exists in scattered form — the work is consolidation, gap-filling (escalation, test plan, communication templates), and cross-referencing. No code changes.

### Testing Requirements
- No automated tests (documentation only)
- **Manual review checklist:**
  - [ ] All `make` commands in runbook are verified against Makefile
  - [ ] All `kubectl`/`helm` commands are syntactically correct
  - [ ] All file paths referenced exist in the repository
  - [ ] RTO/RPO values match `data-engineering.md`
  - [ ] Escalation matrix reviewed by engineering management

---

## Summary

| Story | Title | Original SP | Revised SP | Status | Key Deliverables |
|-------|-------|-------------|------------|--------|------------------|
| #87 / US-10.1 | Automated Database Backups | 5 | 3 | Mostly done | Weekly backup task, metrics, tests, dead code cleanup |
| #88 / US-10.2 | File Storage Backup & Replication | 3 | 2 | Partial | Versioning, lifecycle policies, health check task |
| #86 / US-10.3 | Design Archival to Cold Storage | 3 | 3 | Partial | Archive service, admin API, migration, Celery task |
| #89 / US-10.4 | Disaster Recovery Runbook | 2 | 1 | Partial | Unified runbook, DR test plan, escalation matrix |
| | **Total** | **13** | **9** | | |

### New Files To Create

| File | Story | Purpose |
|------|-------|---------|
| `backend/tests/services/test_backup_service.py` | US-10.1 | BackupService integration tests |
| `backend/tests/core/test_backup.py` | US-10.1 | DatabaseBackup + DataExporter tests |
| `backend/tests/worker/test_backup_tasks.py` | US-10.1 | Backup Celery task tests |
| `backend/app/core/storage_init.py` | US-10.2 | MinIO bucket versioning + lifecycle setup |
| `backend/tests/core/test_storage_init.py` | US-10.2 | Storage init tests |
| `backend/tests/worker/test_storage_health.py` | US-10.2 | Storage health check tests |
| `backend/app/services/design_archive.py` | US-10.3 | Design archival service |
| `backend/app/schemas/archive.py` | US-10.3 | Archive Pydantic schemas |
| `backend/app/api/v1/archives.py` | US-10.3 | Admin archive endpoints |
| `backend/tests/services/test_design_archive.py` | US-10.3 | Archive service tests |
| `backend/tests/api/test_archives.py` | US-10.3 | Archive API tests |
| `backend/tests/worker/test_archive_tasks.py` | US-10.3 | Archive task tests |
| `backend/alembic/versions/xxxx_add_design_archive_columns.py` | US-10.3 | DB migration |
| `docs/operations/disaster-recovery-runbook.md` | US-10.4 | Unified DR runbook |

### Files To Modify

| File | Story | Change |
|------|-------|--------|
| `backend/app/services/backup.py` | US-10.1 | Remove commented-out Celery tasks (lines ~595–659) |
| `backend/app/worker/tasks/maintenance.py` | US-10.1, US-10.2, US-10.3 | Add `weekly_full_backup`, `check_storage_health`, `archive_old_designs` tasks |
| `backend/app/worker/celery.py` | US-10.1, US-10.2, US-10.3 | Add beat schedule entries for new tasks |
| `backend/app/worker/tasks/__init__.py` | US-10.1, US-10.2, US-10.3 | Export new tasks |
| `backend/app/models/design.py` | US-10.3 | Add `archived_at`, `archive_location` columns |
| `backend/app/core/config.py` | US-10.3 | Add `DESIGN_ARCHIVE_AFTER_DAYS` setting |
| `backend/app/api/v1/__init__.py` | US-10.3 | Register archive routes |
| `docs/architecture/data-engineering.md` | US-10.2, US-10.4 | Add versioning/lifecycle docs, link to DR runbook |
| `helm/INGRESS_RUNBOOK.md` | US-10.4 | Cross-reference unified DR runbook |

### Security Considerations (per attached instructions)
- **Archive admin endpoints** must enforce admin-only authorization via `Depends(get_current_admin_user)`
- **Input validation**: Archive/restore endpoints validate UUID format, check design ownership
- **Rate limiting**: Archive restore endpoint should be rate-limited (destructive operation)
- **Logging**: All archive/restore operations create audit log entries
- **No secrets in DR runbook**: Reference `docs/operations/secrets-management.md` rather than including actual credentials
