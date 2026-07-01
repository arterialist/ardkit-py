# Concepts

## How ardkit maps to the ARD spec

| ARD concept | ardkit |
| --- | --- |
| `ai-catalog.json` manifest | `CatalogManifest` / `Catalog.to_dict()` |
| Host info | `HostInfo` |
| Catalog entry | `CatalogEntry` |
| Trust manifest | `TrustManifest`, `Attestation`, `ProvenanceLink`, `TrustSchema` |
| URN `urn:air:<publisher>:<ns>:<name>` | `make_urn()` (auto in the builder) |
| Media types | `ardkit.media_types` |
| Well-known publishing | `mount_ard(...)` |
| Discovery hints (robots/link/DNS) | `ardkit.discovery` |
| `POST /search` `/explore` `GET /agents` | `RegistryService` + FastAPI router |
| JSON Schema conformance | `ardkit.validation` (vendored schema) |

## Value-or-reference

Every entry carries **exactly one** of `url` (a link to the artifact document) or
`data` (the inline artifact). The models enforce this, matching the schema's
`oneOf`.

## Discovery is not invocation

ARD — and ardkit — sit entirely *before* invocation: they help a client find the
right resource. Authentication and the actual call happen over the artifact's own
protocol (MCP, A2A, …). The registry relevance `score` is **not** a trust or
safety rating.

## Conformance

The schemas under `ardkit/schemas/` are vendored verbatim from
[`ards-project/ard-spec`](https://github.com/ards-project/ard-spec). The test
suite validates the builder's output — and the spec's own example catalogs —
against `ai-catalog.schema.json`.
