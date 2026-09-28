# Offline sync

This file contains how the mobile app stores and syncs reading data without a connection:
the local database, the sync protocol with the server, the conflict resolution algorithm,
the retry queue, and download licence checks. Ask here for how questions about sync
endpoints, vector clocks, conflict merging, the outbox queue, and licence expiry checks.

Related: product/offline-reading.md
Owner: mobile team

## Index

1. Local storage — the on-device SQLite schema for positions, highlights, notes and downloads
2. Sync protocol — the /sync endpoint, the change-set format, and the order of a sync round
3. Conflict resolution — the algorithm per record type: max for positions, keep-both for notes and highlights
4. Outbox and retries — how offline changes are queued, retried with backoff, and deduplicated
5. Licence checks — how the 30-day offline licence is stored, checked and renewed

## Local storage

SQLite tables `positions(book_id, cfi, updated_at, device_id)`, `annotations(id uuid, book_id,
kind, body, version_vector, deleted)`, `downloads(book_id, licence_expires_at)`.

## Sync protocol

`POST /sync` with `{device_id, since_token, changes: [...]}` returns `{changes, next_token}`.
A round pushes local changes first, then pulls; `next_token` is stored only after both succeed.

## Conflict resolution

Positions: the larger CFI wins. Annotations: each carries a version vector; concurrent edits
produce a `conflict` record holding both bodies, shown to the user. Deletion is a tombstone,
never a hard delete, so no note is lost by a stale device.

## Outbox and retries

Every local change is written to `outbox` in the same transaction. The sync worker retries
with exponential backoff up to 1 hour, and the server dedups by change id, so replays are safe.

## Licence checks

`downloads.licence_expires_at` is set to now + 30 days on each online check. The reader refuses
to open a book past that timestamp and schedules a check when a connection appears.
