# Roadmap

The core bridge should remain small and auditable. Future work should be modular rather than turning the wake script into a full agent framework.

## v0.2 candidates

- signed/attested completion receipts for multi-user repositories;
- diagnostics UI for delivered, skipped, and duplicate wakes;
- multiple named ChatGPT conversation routes with explicit route authorization;
- pluggable durable control-plane adapters beyond GitHub Issues;
- hardened selector adapter with explicit ChatGPT UI compatibility tests;
- cleaner self-hosted runner installation/health checks;
- optional macOS/Linux wake adapters where an existing authenticated browser can be safely attached;
- optional ephemeral/dedicated runner deployment recipes.

## Longer-term ideas

- provider-neutral `ConversationWakeAdapter` interface;
- controller policy templates for research, CI, benchmarking, and long-running data jobs;
- explicit human-decision gates as machine-readable contracts;
- portable provenance bundles linking task -> receipt -> wake -> next task;
- comparison harness against API-backed agent orchestration;
- stronger receipt provenance using GitHub attestations or signed payloads.

## Non-roadmap

The core project does not aim to:

- scrape or archive ChatGPT answers;
- bypass login/authentication;
- become an unattended auto-merge bot;
- hide the durable source of truth inside browser state;
- accept arbitrary public prose as trusted instructions;
- make scientific claims from CI status alone.
