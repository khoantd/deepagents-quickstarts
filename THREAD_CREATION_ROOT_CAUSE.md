# Root Cause Analysis: Automatic Thread Creation

## Problem

A new LangGraph thread is automatically generated when sending a message, even when an existing thread should be used.

## Root Cause

The issue occurs in `deep-agents-ui/src/app/hooks/useChat.ts` when `stream.submit()` is called:

1. **Missing `thread_id` in config**: When `stream.submit()` is called, the config object doesn't explicitly include `configurable: { thread_id: ... }`.

2. **LangGraph SDK behavior**: The LangGraph SDK automatically creates a new thread when:
   - `stream.submit()` is called without an existing `thread_id` in the config
   - The `useStream` hook is initialized with `threadId: null`
   - The stream hasn't reinitialized after `threadId` changes

3. **Timing issue**: Even when `useStream` is initialized with a `threadId`, if the stream hasn't reinitialized or if `resolvedThreadId` changes, the config passed to `stream.submit()` doesn't include the thread_id, causing LangGraph to create a new thread.

## Technical Details

### Before Fix

```typescript
stream.submit(
  { messages: [newMessage] },
  {
    optimisticValues: (prev) => ({
      messages: [...(prev.messages ?? []), newMessage],
    }),
    config: { ...(activeAssistant?.config ?? {}), recursion_limit: 100 },
    // ❌ Missing: configurable: { thread_id: resolvedThreadId }
  }
);
```

### After Fix

```typescript
// Helper function to build config with thread_id if available
const buildSubmitConfig = (baseConfig?: Record<string, any>, explicitThreadId?: string | null) => {
  const config: Record<string, any> = {
    ...(baseConfig ?? {}),
    recursion_limit: 100,
  };
  
  // Use explicit thread_id if provided, otherwise use resolvedThreadId
  const threadIdToUse = explicitThreadId ?? resolvedThreadId;
  
  // Explicitly set thread_id in configurable if threadId exists
  // This prevents LangGraph from auto-creating a new thread
  if (threadIdToUse) {
    config.configurable = {
      ...(config.configurable ?? {}),
      thread_id: threadIdToUse,
    };
  }
  
  return config;
};

stream.submit(
  { messages: [newMessage] },
  {
    optimisticValues: (prev) => ({
      messages: [...(prev.messages ?? []), newMessage],
    }),
    config: buildSubmitConfig(activeAssistant?.config),
    // ✅ Now includes: configurable: { thread_id: resolvedThreadId }
  }
);
```

## Solution

1. **Created `buildSubmitConfig` helper function**: This function explicitly sets `configurable: { thread_id: ... }` in the config when a thread ID is available.

2. **Updated all `stream.submit()` calls**: All 5 instances of `stream.submit()` in `sendMessage` now use `buildSubmitConfig()` to ensure the thread_id is always passed.

3. **Handled edge case**: When creating a new LangGraph thread for a thread-service-only thread, the new thread ID is passed explicitly to `buildSubmitConfig()` to avoid closure timing issues.

## Impact

- **Before**: LangGraph would create a new thread every time `stream.submit()` was called without an explicit thread_id, even when an existing thread should be used.
- **After**: LangGraph will use the existing thread when `resolvedThreadId` is set, and only create a new thread when `resolvedThreadId` is `null` (intentional new conversation).

## Files Modified

- `deep-agents-ui/src/app/hooks/useChat.ts`: Added `buildSubmitConfig()` helper and updated all `stream.submit()` calls to use it.

## Testing Recommendations

1. **Existing thread**: Select an existing thread and send a message - should continue the conversation in the same thread.
2. **New conversation**: Clear thread selection and send a message - should create a new thread (expected behavior).
3. **Thread-service-only thread**: Select a thread that only exists in thread service (no LangGraph thread) - should create LangGraph thread and use it.
4. **Thread switching**: Switch between threads and send messages - each should use the correct thread.

