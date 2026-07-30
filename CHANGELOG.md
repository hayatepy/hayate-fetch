# Changelog

All notable changes to hayate-fetch are documented here.

## [0.1.4] - 2026-07-30

### Changed

- Route package discovery, start, and tested-compatibility links through
  `hayatepy.dev`, including the PyPI project homepage.

## [0.1.3] - 2026-07-26

### Changed

- Link the canonical ecosystem start page, production golden app, and tested
  compatibility evidence from the published package description.

## [0.1.2] - 2026-07-24

### Changed

- Mark the distribution as typed, validate the public source with strict
  mypy in CI, and keep Workers-only imports lazy and type-checkable.
- Match Fetch redirect semantics for 301/302/303/307/308 and prevent
  `Authorization`, `Cookie`, and proxy credentials from crossing origins.
- Expose the same validated follow/manual redirect policy on the CPython and
  Workers backends.
- Audit locked dependencies on every change and publish an SPDX SBOM plus
  GitHub build and SBOM attestations with each release.

## [0.1.1] - 2026-07-24

### Changed

- Align package metadata and the protected release path.

## [0.1.0] - 2026-07-23

### Added

- Add WHATWG-shaped client-side `fetch`, a standard-library CPython backend,
  a Cloudflare Workers backend, and the injectable `FetchBackend` protocol.
