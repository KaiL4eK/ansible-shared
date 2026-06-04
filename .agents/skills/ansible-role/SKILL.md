---
name: ansible-role
description: Use when creating, refactoring, or reviewing Ansible roles inside ansible-shared, especially under roles/, including tasks, defaults, handlers, variable flow, idempotency, and role interface design.
---

# Ansible Shared Role Development

## Overview

Use this skill to implement or refine reusable Ansible roles in this repository.

The goal is to produce small, predictable, idempotent roles with a clear input contract and no hidden dependency on environment-specific state.

## Context Discovery

1. Read `AGENTS.md` for local repository rules.
2. Read `README.md` for the repository overview and current content.
3. Inspect existing roles under `roles/` before introducing a new pattern.

## When to Use

- Creating a new role under `roles/`.
- Refactoring role tasks, defaults, or handlers.
- Fixing role idempotency or variable contract issues.
- Improving a role so it can be reused across inventories or playbooks.
- Reviewing whether logic belongs in a shared role instead of an environment-specific playbook.

## Repository Context

- This repository is a shared role library.
- Keep environment-specific inventory, vault wiring, and orchestration outside these roles.
- Shared roles should expose a clean interface through defaults and explicit vars overrides.

## Role Contract

For most roles, use this structure:

- `roles/<domain>/<role>/tasks/main.yml`
- `roles/<domain>/<role>/defaults/main.yml`
- `roles/<domain>/<role>/handlers/main.yml` when restart/reload hooks are needed
- `roles/<domain>/<role>/meta/main.yml` when metadata or dependencies are needed

Add `templates/`, `files/`, or `vars/` only when required by the role behavior.

## Creating a New Role

- Choose the target domain under `roles/<domain>/` first.
- Role names must use `kebab-case`.
- Create the role scaffold with `ansible-galaxy role init roles/<domain>/<role-name>`.
- Keep the generated structure minimal and remove unused files only when they are not needed.

## Variable Rules

- Put overridable inputs in `defaults/main.yml`.
- Treat `defaults/main.yml` as the role input surface, not as a value store that playbooks should read back from later.
- Variables flow only from playbook or inventory into the role.
- If the same value is needed both by a playbook and by the role, declare it in play vars, inventory, or vault and pass it into the role explicitly through `vars:`.
- The role must not depend on undeclared external variables.
- Do not assume `include_role` exports role defaults or role vars back into the playbook.

## Secrets and Safety

- Never hardcode tokens, passwords, or other secrets in role files.
- Keep privileged credentials outside the role unless there is a clear reason they belong to the role interface.
- If a service needs database provisioning, keep `roles/postgresql/*` orchestration in the playbook rather than embedding it inside the shared service role.

## Working Style

- Prefer idempotent modules over `shell` or `command` when a module exists.
- Use FQCN module names.
- Keep task names explicit and outcome-focused.
- Use handlers for restart or reload actions triggered by changed files or configs.
- Add `changed_when` or `failed_when` when command-like tasks need precise behavior.
- Keep diffs small and consistent with existing roles.

## Implementation Workflow

1. Define the desired end state and what part of it belongs inside a reusable role.
2. For a new role, create `roles/<domain>/` if needed and run `ansible-galaxy role init roles/<domain>/<role-name>`.
3. Design the role interface first: defaults, required overrides, files, templates, and handlers.
4. Implement the minimal task set needed to reach the target state safely on re-run.
5. Check for hidden coupling to inventory, vault files, or playbook-local variables.
6. Validate YAML and Ansible behavior before handoff.

## Good Patterns

### Role defaults as interface

```yaml
# roles/example/defaults/main.yml
example_image: nginx:stable
example_container_name: example
```

### Handler-driven restart

```yaml
- name: Render config
  ansible.builtin.template:
    src: example.conf.j2
    dest: /etc/example/example.conf
  notify: Restart example
```

```yaml
# roles/example/handlers/main.yml
- name: Restart example
  ansible.builtin.service:
    name: example
    state: restarted
```

### Controlled command task

```yaml
- name: Query runtime status
  ansible.builtin.command: examplectl status --short
  register: example_status
  changed_when: false
```

## Common Mistakes

- Using short module names instead of FQCN.
- Hardcoding environment-specific values in tasks.
- Using `shell` for file, package, service, or container operations that have native modules.
- Omitting handlers after changing config files.
- Writing command tasks without `changed_when` when they are read-only.
- Reading `role_prefix_*` variables from playbook tasks when those values only exist in role defaults.
- Relying on undeclared variables that are not present in the role defaults and are not passed explicitly.
- Hiding playbook-level DB/user creation inside a shared service role.

## Validation

Run validation from the repository root:

```bash
yamllint <file-or-dir>
pdm run ansible-lint
```

Use the available checks that make sense for the role being changed.

## Output Expectations

When delivering changes:

- Point to the updated role files.
- Explain the role interface that was added or changed.
- Mention any handler, defaults, or template implications.
- State which validations were run and which were not applicable.
