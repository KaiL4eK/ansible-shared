# Hermes Todoist MCP role

Installs the official local `@doist/todoist-mcp` server and configures it in
Hermes. Requires Node.js 24+ and npm 11+ (use `nodejs/runtime` first), an
installed Hermes agent, privilege escalation, and `community.general`.

The API key is supplied by Ansible, written to the Hermes user's `.env` with
mode `0600` via `hermes/agent_env`, and hidden from task output. The MCP entry
uses `${TODOIST_API_KEY}` so `config.yaml` never stores the key. Both shared
Hermes roles restart the gateway only when their configuration changes.

## Defaults and inputs

- `hermes_todoist_mcp_api_key: null` — **required**; pass from a vault or other
  external secret source.
- `hermes_todoist_mcp_user: hermes`,
  `hermes_todoist_mcp_user_home: /home/hermes`,
  `hermes_todoist_mcp_home: /home/hermes/.hermes` — service user and paths.
- `hermes_todoist_mcp_package: "@doist/todoist-mcp"`,
  `hermes_todoist_mcp_version: "13.1.3"`,
  `hermes_todoist_mcp_install_dir: /opt/hermes-todoist-mcp` — npm package.
- `hermes_todoist_mcp_server_name: todoist` — Hermes MCP server name.

## Usage

```yaml
- hosts: hermes_hosts
  become: true
  vars:
    hermes_todoist_mcp_api_key: "{{ vault_todoist_api_key }}"
roles:
  - nodejs/runtime
  - hermes/agent_todoist_mcp
```

For `ansible/playbooks/hermes/vova-hermes.yml`, supply
`vault_hermes_vova_todoist_api_key` from an external vaulted vars file or
inventory. For example, run from `ansible/`:

```bash
pdm run ansible-playbook playbooks/hermes/vova-hermes.yml --extra-vars @/secure/vova-secrets.yml
```

The vaulted vars file must define `vault_hermes_vova_todoist_api_key`.
