# Changelog

All notable changes to hayate-fetch are documented here.

## [0.1.2] - 2026-07-24

### Changed

- Mark the distribution as typed, validate the public source with strict
  mypy in CI, and keep Workers-only imports lazy and type-checkable.

## [0.1.1] - 2026-07-24

### Changed

- Align package metadata and the protected release path.

## [0.1.0] - 2026-07-23

### Added

- Add WHATWG-shaped client-side `fetch`, a standard-library CPython backend,
  a Cloudflare Workers backend, and the injectable `FetchBackend` protocol.
