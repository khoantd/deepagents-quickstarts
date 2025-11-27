# Thread Persistence Analysis: Why Threads Weren't Saved and Loaded

## Overview

This document explains the root causes of why threads were not being saved to and loaded from the database.

## Root Causes

### 1. **Authentication Required (Primary Issue)**

**Problem**: Thread persistence requires user authentication. If a user is not logged in, threads will NOT be saved.

**Location**: `deep-agents-ui/src/app/hooks/useThreadPersistence.ts:154`

```typescript
if (!THREAD_SERVICE_BASE_URL || !threadId || messages.length === 0 || !accessToken) {
  return; // Persistence is skipped if accessToken is missing
}
```

**Impact**:
- Threads created before authentication was added won't be visible
- Users must be logged in for threads to persist
- Anonymous users' threads are lost on page refresh

**Solution**: This is by design for security, but users should be aware that authentication is required.

---

### 2. **Environment Variable Configuration**

**Problem**: If `NEXT_PUBLIC_THREAD_SERVICE_URL` is not set, thread persistence is completely disabled.

**Location**: `deep-agents-ui/src/app/hooks/useThreadPersistence.ts:6-7`

```typescript
const THREAD_SERVICE_BASE_URL =
  process.env.NEXT_PUBLIC_THREAD_SERVICE_URL?.replace(/\/$/, "") || null;
```

**Impact**:
- Threads won't be saved if the environment variable is missing
- No error message is shown to the user
- Falls back silently to LangGraph-only mode

**Solution**: Ensure `NEXT_PUBLIC_THREAD_SERVICE_URL` is set in `.env.local` or environment configuration.

---

### 3. **User ID Filtering (Historical Threads)**

**Problem**: Threads created before authentication was added have `user_id = NULL` and are filtered out when listing threads.

**Location**: `thread_service/thread_service/repositories.py:422`

```python
.where(Thread.user_id == user_id)  # This excludes NULL user_id threads
```

**Impact**:
- Old threads (created before authentication) won't appear in the thread list
- These threads exist in the database but are invisible to users
- See `ROOT_CAUSE_ANALYSIS.md` for details

**Solution**: 
- Run a data migration to assign old threads to users
- Or modify the query to include threads with NULL user_id for the current user (if applicable)

---

### 4. **Thread Creation Only When Messages Exist**

**Problem**: Threads are only created in the database when there are messages.

**Location**: `deep-agents-ui/src/app/hooks/useThreadPersistence.ts:154`

```typescript
if (!THREAD_SERVICE_BASE_URL || !threadId || messages.length === 0 || !accessToken) {
  return;
}
```

**Impact**:
- Empty threads (no messages yet) won't be persisted
- Threads are created only after the first message is sent
- This is actually correct behavior, but worth noting

---

### 5. **Message Syncing Depends on Thread Creation**

**Problem**: Messages can only be synced if the thread exists in the thread service.

**Location**: `deep-agents-ui/src/app/hooks/useThreadPersistence.ts:274-282`

```typescript
const serviceThreadId = threadIdMapRef.current[threadId] ?? (await ensureThreadExists());

if (!serviceThreadId) {
  console.warn("[ThreadService] Cannot sync messages because thread-service UUID is unknown");
  return; // Messages won't be synced if thread doesn't exist
}
```

**Impact**:
- If thread creation fails, messages won't be synced
- Messages are only synced after thread is successfully created
- Silent failures can occur if thread creation fails

---

### 6. **Thread Loading Requires Authentication**

**Problem**: Threads are only loaded from the database when the user is authenticated.

**Location**: `deep-agents-ui/src/app/hooks/useThreads.ts:65-69`

```typescript
const useThreadService = !!(
  THREAD_SERVICE_BASE_URL &&
  accessToken &&
  config
);
```

**Impact**:
- Unauthenticated users only see LangGraph threads
- Database threads are invisible without authentication
- Falls back to LangGraph-only mode silently

---

### 7. **Thread Resolution Issues (Fixed)**

**Problem**: Old threads without `langgraph_thread_id` in metadata were marked as read-only.

**Location**: `deep-agents-ui/src/app/hooks/useChat.ts:103-109` (now fixed)

**Impact**:
- Old threads couldn't be continued
- Users saw "read-only" error message
- **This has been fixed** - threads now try using UUID as LangGraph ID

---

## Summary of Requirements for Thread Persistence

For threads to be saved and loaded from the database, ALL of the following must be true:

1. ✅ User must be authenticated (`accessToken` must exist)
2. ✅ `NEXT_PUBLIC_THREAD_SERVICE_URL` environment variable must be set
3. ✅ Thread service must be running and accessible
4. ✅ Thread must have at least one message
5. ✅ Thread must have a valid `threadId` (LangGraph thread ID)
6. ✅ User must own the thread (for loading - threads are filtered by `user_id`)

## Common Failure Scenarios

### Scenario 1: User Not Logged In
- **Symptom**: Threads appear in UI but disappear after refresh
- **Cause**: No `accessToken`, so persistence is skipped
- **Fix**: User must log in

### Scenario 2: Environment Variable Missing
- **Symptom**: Threads work but aren't saved to database
- **Cause**: `NEXT_PUBLIC_THREAD_SERVICE_URL` not set
- **Fix**: Set environment variable in `.env.local`

### Scenario 3: Old Threads Not Visible
- **Symptom**: Historical threads don't appear in sidebar
- **Cause**: Threads have `user_id = NULL` and are filtered out
- **Fix**: Run data migration to assign threads to users

### Scenario 4: Thread Service Not Running
- **Symptom**: Thread creation fails silently
- **Cause**: Thread service API is unreachable
- **Fix**: Start thread service (`cd thread_service && uv run python run.py`)

## Recommendations

1. **Add Better Error Logging**: Currently, many failures are silent. Add console warnings/errors when persistence fails.

2. **User Feedback**: Show a notification when threads can't be persisted (e.g., "Threads won't be saved - please log in").

3. **Data Migration**: Create a migration to assign old threads (with NULL user_id) to the first user or a system user.

4. **Health Check**: Add a health check endpoint to verify thread service is accessible before attempting persistence.

5. **Retry Logic**: Add retry logic for failed thread creation/message syncing operations.

6. **Offline Support**: Consider storing threads in localStorage as a fallback when thread service is unavailable.

