# Papis Integration Branch Repair Design

**Date:** 2026-04-01
**Branch:** `feature/papis-integration`
**Scope:** Restore Claude Code marketplace installability for the papis branch while preserving branch-specific packaging identity

## Overview

This design narrows the current work to two coupled goals:

1. Make `feature/papis-integration` install in Claude using the same workflow as `main`:
   - `plugin marketplace add ...`
   - `plugin install ...`
2. Keep the papis branch install distinct from the main plugin package while showing the same human-facing marketplace name in Claude's plugin list.

The current branch is in a split state:

- `main` uses the legacy `.claude-plugin/` packaging layout for marketplace installs
- `feature/papis-integration` deleted `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
- The branch also contains a newer `claude/` manifest layout, but that is not the proven marketplace path used by `main`

The repair strategy is to restore `.claude-plugin/` as the authoritative Claude marketplace packaging layer for this branch and align it with the papis-enabled branch contents.

## Goals

- Restore a working Claude marketplace install path on `feature/papis-integration`
- Keep the visible marketplace/plugin name the same as `main`
- Use a branch-specific install identity so the papis branch does not collide with the main plugin
- Point marketplace metadata at the papis branch source rather than `main`
- Ensure installed assets match what the branch actually ships

## Non-Goals

- No unrelated refactoring of the repository layout
- No attempt to fully migrate marketplace installs to the newer `claude/` manifest format
- No change to the approved target branch name; `feature/papis-integration` remains the working branch

## Current State

Observed repository state at design time:

- Active branch: `feature/papis-integration`
- There is no local or remote `feature/papis-parser` branch
- Tracked deletions exist for:
  - `.claude-plugin/marketplace.json`
  - `.claude-plugin/plugin.json`
  - `claude/.claude-plugin`
- `main` contains working `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
- `feature/papis-integration` already contains papis-related spec and manifest changes under `claude/`

This indicates the branch lost the exact files used by the known-working Claude marketplace flow.

## Recommended Approach

### Option Chosen

Restore and standardize on the legacy `.claude-plugin/` layout for marketplace installation on this branch.

### Why This Option

- It matches the known-working installation model on `main`
- It minimizes risk compared with inventing a new install path
- It allows a distinct install id while preserving the marketplace-facing display name
- It addresses the branch's actual regression directly: deleted marketplace metadata files

## Packaging Design

### Authoritative Install Layout

`feature/papis-integration` will ship Claude marketplace metadata from `.claude-plugin/`.

The `claude/` directory may still remain as a source of command assets and branch metadata, but the Claude marketplace add/install flow should be driven by `.claude-plugin/` because that is the structure already proven on `main`.

### Identity Rules

Two names matter and they serve different purposes:

- **Display name**
  - What users see in the Claude marketplace list
  - This should remain the same as `main`
- **Install identity**
  - The plugin package id users pass to `plugin install ...`
  - This must be branch-specific so the papis branch installs separately from the main plugin

### Proposed Naming Model

- Marketplace-visible name: same as `main`
- Branch-specific plugin id: a papis-specific variant, for example `bibliography-skills-papis`

The exact install string will be finalized from the metadata format already used on `main`, but the design requirement is fixed:

- same visible listing name
- different installable package identity

### Metadata Responsibilities

`.claude-plugin/plugin.json`
- Holds the branch-specific plugin identity and versioned package metadata
- Must identify the papis branch package, not the mainline package

`.claude-plugin/marketplace.json`
- Holds marketplace listing metadata
- Must preserve the same human-facing marketplace name used on `main`
- Must list the papis branch plugin package as the install target
- Must point source/repository fields at the papis branch content

## Source Mapping

The marketplace metadata for this branch must resolve to the papis branch source.

That means:

- repository/homepage/source fields cannot silently resolve to `main`
- branch-aware source references must be used where the Claude marketplace format expects them
- if the marketplace metadata is relative-path based, it must still package the current branch's files rather than depending on deleted paths

## Asset Consistency Requirements

The install metadata must match the actual files present on `feature/papis-integration`.

Checks required before implementation is considered complete:

- Commands referenced by Claude metadata exist on disk
- Python scripts referenced by commands exist on disk
- Manifest/version fields are internally consistent
- No install metadata points at deleted `.claude-plugin` artifacts or stale paths
- The papis branch command surface is the one users receive after install

## Implementation Outline

1. Compare `.claude-plugin/` files on `main` against the current branch
2. Restore `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` on `feature/papis-integration`
3. Change plugin identity to a branch-specific install id
4. Keep the visible marketplace listing name unchanged
5. Update repository/source metadata to resolve against the papis branch
6. Reconcile metadata with current branch command/script layout
7. Verify the branch supports the same install flow as `main`

## Error Handling

Primary failure cases to guard against:

- Marketplace add succeeds but install targets the wrong package id
- Marketplace listing name changes unexpectedly
- Install resolves to `main` instead of `feature/papis-integration`
- Metadata references files removed from the branch
- Duplicate package identity causes collision with the main plugin

## Testing Strategy

Verification for this work is metadata and packaging focused rather than feature focused.

### Required Verification

- Inspect `main` and `feature/papis-integration` metadata side-by-side
- Confirm `.claude-plugin/plugin.json` exists and uses the branch-specific install id
- Confirm `.claude-plugin/marketplace.json` exists and retains the same visible listing name as `main`
- Confirm source/repository metadata references the papis branch package content
- Confirm commands/scripts referenced by the installed package exist

### Practical Validation

If Claude CLI/plugin tooling is available in the environment, validate the exact expected user flow:

1. `plugin marketplace add ...`
2. `plugin install ...`

If live CLI validation is not available, validate the on-disk metadata structure against the known-working `main` branch contract and document the remaining runtime risk.

## Risks

- Claude marketplace metadata behavior is not fully documented publicly, so preserving the `main` structure is the safest route
- The branch currently mixes old and new packaging conventions; partial fixes may leave install behavior ambiguous
- Branch-specific naming must avoid collisions while still being understandable to the user

## Decision Summary

- Target branch is `feature/papis-integration`
- The repair follows the `main` branch's `.claude-plugin/` marketplace pattern
- The visible marketplace name stays the same as `main`
- The install identity becomes branch-specific
- The work stays focused on marketplace/install correctness and branch packaging integrity
