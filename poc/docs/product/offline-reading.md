# Offline reading

This file contains the product rules for the mobile app when it has no connection: what a
customer can do offline, what happens to their highlights and notes, and who wins when two
devices disagree. Ask here for why questions about offline behaviour, lost annotations,
sync conflicts between phone and tablet, and downloads expiring.

Related: engineering/offline-sync.md
Owner: mobile

## Index

1. What works offline — which app actions work without a connection and which are refused, and why the line is where it is
2. Conflicts between devices — the promise about whose changes win when a phone and a tablet both edited offline
3. Downloads and expiry — how long a downloaded book stays readable offline and why it expires at all
4. What we tell the customer — the wording rules for offline states and sync errors

## What works offline

Reading, highlighting, notes and bookmarks work offline. Buying, reviews and following an
author do not; they are refused with a clear message rather than queued, because a purchase
that silently happens hours later has caused chargebacks. Reading position syncs when back
online.

## Conflicts between devices

Reading position: the furthest position wins. Highlights and notes: both are kept, never
merged into one and never silently dropped; if the same highlight was edited on both devices
the customer sees both versions and picks. We promised "you will never lose a note" in the
app store listing, so any conflict rule that discards a note is a breach.

## Downloads and expiry

A downloaded book stays readable for 30 days offline, then needs one online check. The
expiry exists because of publisher licensing terms, not our choice; the 30 days is the most
generous term across our publisher contracts.

## What we tell the customer

Offline states say what still works, not what is broken: "You're offline. Reading and notes
still work." Sync errors never show technical detail and always offer "try again". We never
use the word "lost".
