# Vendored ARD spec schemas

These files are copied verbatim from the canonical ARD specification repository
[`ards-project/ard-spec`](https://github.com/ards-project/ard-spec) (`main`) so
that `ardkit` can validate manifests offline and stay pinned to a known spec
revision.

| File | Upstream path |
| --- | --- |
| `ai-catalog.schema.json` | `spec/schemas/ai-catalog.schema.json` |
| `ard.cddl` | `spec/schemas/ard.cddl` |
| `ard.openapi.yaml` | `spec/schemas/ard.openapi.yaml` |
| `SPEC_VERSION` | `specVersion` value these schemas target |

ARD spec is licensed under Apache-2.0. To refresh, re-run
`scripts/vendor_schemas.py` (see repo root) and review the diff.
