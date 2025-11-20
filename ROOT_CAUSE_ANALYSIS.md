# Root Cause Analysis: Historical Threads Not Visible in Sidebar

## Problem
Users cannot see historical threads in the left sidebar after authentication was added to the thread service.

## Root Cause

### Primary Issue: NULL user_id in Historical Threads

1. **Migration History**: The migration `20251120_232056_add_users.py` added a `user_id` column to the `threads` table as **nullable** initially (line 168):
   ```python
   nullable=True,  # Allow null initially for existing threads
   ```

2. **Existing Data**: Threads created before this migration have `user_id = NULL` in the database.

3. **Query Filtering**: The `list_threads` function in `repositories.py` filters threads by user_id:
   ```python
   .where(Thread.user_id == user_id)
   ```
   This SQL condition **excludes threads with NULL user_id** because `NULL == user_id` evaluates to `NULL` (not `TRUE`), so those rows are filtered out.

4. **Model Constraint**: While the SQLAlchemy model now requires `user_id` to be non-null (`nullable=False`), existing database rows may still have NULL values.

### Secondary Issues

1. **gRPC API Broken**: The gRPC API methods (`CreateThread`, `ListThreads`, `GetThread`) are missing the required `user_id` parameter after the authentication migration.

2. **Frontend Error Handling**: Limited error logging makes it difficult to diagnose authentication or API issues.

## Solution

### Immediate Fix: Data Migration

Create a data migration to handle threads with NULL user_id:

1. **Option A (Recommended)**: Assign NULL user_id threads to the first user in the system (if only one user exists)
2. **Option B**: Delete threads with NULL user_id (if they're truly orphaned)
3. **Option C**: Create a default "system" user and assign orphaned threads to it

### Long-term Fixes

1. Fix gRPC API methods to require authentication and user_id
2. Add better error logging in frontend
3. Ensure all new threads are created with user_id

## Files Affected

- `thread_service/thread_service/repositories.py` - Query filters out NULL user_id
- `thread_service/migrations/versions/20251120_232056_add_users.py` - Migration allows NULL initially
- `thread_service/thread_service/api/grpc.py` - Missing user_id parameter
- `deep-agents-ui/src/app/hooks/useThreads.ts` - Error handling improvements needed

## Verification Steps

1. Check database for threads with NULL user_id:
   ```sql
   SELECT COUNT(*) FROM threads WHERE user_id IS NULL;
   ```

2. Check if accessToken is available in frontend (check browser console)

3. Check if thread service URL is configured (check `NEXT_PUBLIC_THREAD_SERVICE_URL`)

4. Verify authentication is working (check `/auth/me` endpoint)

