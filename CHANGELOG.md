# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `publish(app, host=..., publisher=..., base_url=...)`: one-call FastAPI
  integration. It never mounts anything — it reads the route table, maps each
  already-mounted FastMCP back to its instance (identity-based, via fastmcp's
  `app.state.fastmcp_server`/`path`), introspects tool names into `capabilities`,
  and builds public URLs from `base_url` + the mount path. `introspect=True`
  (default) exposes every mounted MCP; `mcps=[...]` selects instances (unmounted
  ones are ignored); `agents=[...]` adds A2A cards.
- `mounted_mcps(app)` — public helper returning `(server, endpoint_path)` for every
  FastMCP mounted on a FastAPI app, read fresh each call. Use it to build a
  *dynamic* catalog source for hosts whose MCPs mount/unmount at runtime.
- `add_catalog_route()` and caching on `mount_ard`: the manifest is served with a
  weak `ETag` + `Cache-Control` (`DEFAULT_CATALOG_CACHE`) and answers conditional
  `If-None-Match` with `304`. Use `add_catalog_route(app, src, path=...)` to expose
  the catalog *document origin* on a backend host (content-origin / edge-publisher
  split) while discovery is published on the apex.

### Changed
- `mcp_tool_names` now reads FastMCP v2's synchronous `_tool_manager._tools` (and
  still the official mcp SDK's `list_tools()`), never awaiting — so `capabilities`
  are populated for real FastMCP servers.
- The `InMemorySearchProvider` `GET /agents` `filter` is now a **CEL** expression
  (e.g. `type == "..." && "x" in tags`), evaluated with `cel-python` — replacing
  the previous regex. `cel-python` is a core dependency.

### Removed
- The `ardkit` CLI. Validation is available as a library call
  (`ardkit.validation.validate_manifest`).

### Initial
- Initial release of `ardkit` (PyPI: `ardkit-ai`).
- Spec models for `ai-catalog.json` (`specVersion 1.0`): manifest, host, entries,
  trust manifest, with URN / `url`-XOR-`data` / `representativeQueries` validation.
- `Catalog` builder with URN minting and `add_mcp_server` / `add_a2a_agent` /
  `add_skill` / `add_registry` helpers.
- Framework adapters: `from_mcp_server`, `from_fastmcp`, `from_ag2_agent`.
- FastAPI integration `mount_ard` (well-known manifest, robots `Agentmap`, registry).
- Registry layer: `SearchProvider` protocol, `RegistryService`, FastAPI router,
  `InMemorySearchProvider`, filter/facet/score helpers.
- Discovery helpers (robots, `<link>`, DNS records).
- JSON Schema conformance validation against vendored ARD schemas.
