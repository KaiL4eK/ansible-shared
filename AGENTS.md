# Development Rules for `ansible-shared`

## Scope

This repository contains reusable Ansible roles. Keep changes generic, reusable, and independent from environment-specific inventory, vaults, and orchestration.

## Repository Layout

- `roles/` contains shared roles grouped by domain.
- `.agents/skills/ansible-role/SKILL.md` contains the detailed role implementation workflow.
- `requirements.yml` defines role and collection dependencies for this repository.

## Working Rules

- Use this file for repository-level rules and use `.agents/skills/ansible-role/SKILL.md` for role authoring workflow.
- Treat `roles/<domain>/<role-name>` as the standard role layout in this repository.
- Keep deployment-specific values outside roles and pass them in explicitly from the consumer.
- Keep external dependencies declared in `requirements.yml`.
- Do not add environment-specific playbooks, inventory, or vault content here.

## Validation

- Run checks from the repository root.
- Validate YAML with `yamllint`.
- Prefer `pdm run ansible-lint` for Ansible linting.

## How Agents Should Use This Map

1. Read this file first for repository boundaries.
2. Use `.agents/skills/ansible-role/SKILL.md` when creating or changing roles.
3. Keep changes minimal and aligned with the existing structure under `roles/`.
