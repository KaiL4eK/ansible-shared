# ansible-shared

Reusable Ansible roles for shared automation.

## Purpose

`ansible-shared` is a small library of reusable Ansible roles that can be consumed from different playbook collections.

This repository should contain generic role logic, not environment-specific inventory, vault content, or orchestration glue.

## Structure

- `roles/` contains shared roles grouped by domain using `roles/<domain>/<role-name>`.
- `.agents/skills/` contains local skills for implementing and reviewing shared roles.
- `requirements.yml` defines external role and collection dependencies for this repository.
- `AGENTS.md` contains local development rules.
- `LICENSE` defines reuse terms for this repository.

## Preparation

Before working with this repository, install Ansible dependencies:

`ansible-galaxy collection install -r requirements.yml`

## Local Skills

- `.agents/skills/ansible-role/SKILL.md` describes how to create and refine roles in this repository.

## Current Content

- `roles/docker/nfs-server/` provides a shared Docker-based NFS server role.
- `roles/docker/engine/` устанавливает Docker Engine и Docker Compose и
  управляет доступом к группе `docker`.
- `roles/k8s/postgresql-backup-monitoring/` provides shared Kubernetes backup
  monitoring for PostgreSQL.
- `roles/hermes/agent_init/` installs and configures a Hermes Agent user
  service.
- `roles/hermes/agent_env/` manages explicit Hermes environment values in the
  user-owned `.env` file.
- `roles/hermes/agent_mcp/` manages one MCP server entry in the Hermes
  configuration without storing secret values in it.
- `roles/hermes/agent_memory/` manages the built-in Hermes memory and user
  profile character limits without modifying stored memory content.
- `roles/hermes/agent_tavily/` configures the Tavily environment token through
  `roles/hermes/agent_env/` and selects the web backend for Hermes.
- `roles/hermes/agent_tool_loop/` manages the Hermes tool-loop hard-stop
  setting.
- `roles/hermes/git_backup/` configures the Hermes Git backup repository,
  scheduler and `GITHUB_BACKUP_TOKEN` environment value.
- `roles/hermes/git_restore/` restores a Hermes home directory from the Git
  backup repository without overwriting existing data.
