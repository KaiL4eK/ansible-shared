# Node.js runtime role

Installs Node.js from the NodeSource APT repository on supported Debian and
Ubuntu hosts. Verifies the installed Node.js and npm versions, including when
`nodejs` was already present. Requires privilege escalation and gathered facts.

## Defaults

- `nodejs_runtime_major_version: 24` — NodeSource major release.
- `nodejs_runtime_minimum_npm_major_version: 11` — required npm major version.
- `nodejs_runtime_key_url`, `nodejs_runtime_key_path`, and
  `nodejs_runtime_sources_path` — repository configuration.

## Usage

```yaml
roles:
  - nodejs/runtime
```
