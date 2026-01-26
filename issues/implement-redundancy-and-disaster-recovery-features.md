## Implement Redundancy and Disaster Recovery Features

Build systems and workflows to ensure recovery from user mistakes or platform/environmental failures.

### Status: ✅ COMPLETED (Sprint 35)

### Tasks:
1. ✅ Add support for file versioning with the ability to restore prior versions.
   - Existing: `DesignVersion` model with full version history
   - Existing: `versions.py` API with restore endpoint
2. ✅ Implement a trash bin or archive system for restoring accidentally deleted files.
   - Existing: `SoftDeleteMixin` with soft delete/restore
   - Existing: `trash.py` API for listing, restoring, permanent delete
   - Added: Scheduled `purge_expired_trash` task (daily)
3. ✅ Integrate automated backups and regional replication for key design data.
   - Existing: `backup.py` with pg_dump, S3 upload, retention
   - Existing: Celery `backup_database` task (daily)
   - Added: `verify_backups` scheduled task (weekly)
4. ✅ Perform regular integrity checks and provide options for users to export their files and data.
   - Added: `DataIntegrityService` with comprehensive checks
   - Added: `check_data_integrity` scheduled task (weekly)
   - Added: `/api/v1/exports` API for GDPR-compliant user data export
5. ✅ Notify users of impending deletion from Trash.
   - Added: `TRASH_DELETION_WARNING` email template
   - Added: `send_trash_deletion_warnings` task (daily, 7/3/1 day warnings)
   - Added: Frontend `TrashPage` with expiring items banner

### Implementation Details

**Backend Files Created/Modified:**
- `app/services/integrity.py` - DataIntegrityService for orphaned records, missing files, checksums
- `app/api/v1/exports.py` - User data export API endpoints
- `app/worker/tasks/maintenance.py` - Added 4 new scheduled tasks:
  - `purge_expired_trash` - Daily cleanup of expired trash items
  - `send_trash_deletion_warnings` - Daily email notifications
  - `check_data_integrity` - Weekly integrity checks
  - `verify_backups` - Weekly backup verification
- `app/services/email.py` - Added `TRASH_DELETION_WARNING` template

**Frontend Files Created:**
- `src/pages/TrashPage.tsx` - Full-featured trash management UI
- `src/hooks/useTrash.ts` - React Query hook for trash operations
- `src/lib/api/trash.ts` - Trash API client
- `src/components/ui/table.tsx` - Table component
- `src/components/ui/slider.tsx` - Slider component
- `src/components/ui/switch.tsx` - Switch component

**Celery Beat Schedule Updates:**
- `purge-expired-trash`: 86400s (daily)
- `send-trash-deletion-warnings`: 86400s (daily)
- `check-data-integrity`: 604800s (weekly)
- `verify-backups`: 604800s (weekly)

### Outcome
A robust redundancy and recovery system that protects user data from accidental or platform-environmental loss.

**Priority:** Low
**Expected Timeline:** 3 weeks
**Actual Completion:** 1 session