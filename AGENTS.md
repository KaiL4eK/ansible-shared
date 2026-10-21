# Development Rules for `ansible-shared`

## Scope

This repository contains reusable Ansible roles. Keep changes generic, reusable, and independent from environment-specific inventory, vaults, and orchestration.

## Repository Layout

- `roles/` contains shared roles grouped by domain.
- `.agents/skills/ansible-role/SKILL.md` contains the detailed role implementation workflow.
- `requirements.yml` defines role and collection dependencies for this repository.
- `roles/hermes/kubeconfig/` installs an explicitly supplied controller-side
  kubeconfig for an existing managed-host user. Inputs are
  `hermes_kubeconfig_source` (required absolute path), `hermes_kubeconfig_user`
  (`hermes`), `hermes_kubeconfig_group` (defaults to that user), and
  `hermes_kubeconfig_user_home` (`/home/<user>`).

## Working Rules

- PostgreSQL bootstrap (напрямую и через Kubernetes Job) создаёт только
  отсутствующие user/DB. Никогда не менять пароль/атрибуты существующего
  пользователя или владельца существующей БД. До создания БД проверять
  application credentials; при ошибке падать, не исправлять пароль.
  Успешный вход без парольной аутентификации не подтверждает совпадение пароля:
  контрольный вход с неверным паролем должен отклоняться. Проверять оба пути
  интеграционными тестами с сохранением исходного хеша пароля.

- Дашборды Grafana доставляются только через ConfigMap/sidecar; папки создаёт
  provisioning по `grafana_folder`. Не добавлять в роль дашбордов API Grafana,
  admin user/password или зависимость от Grafana vault.
- Use this file for repository-level rules and use `.agents/skills/ansible-role/SKILL.md` for role authoring workflow.
- Treat `roles/<domain>/<role-name>` as the standard role layout in this repository.
- Кластерный PostgreSQL bootstrap выполняет `roles/k8s/postgresql_init_db`: плейбук передаёт credentials и настройки, роль валидирует входы, создаёт уникальный временный Secret, запускает Job и удаляет Secret в `always` (`no_log: true`, `diff: false`). Credentials Job получает только через `secretKeyRef`, не через args, SQL или ConfigMap. Сохранять совместимость режима готовых Secrets: в нём роль не создаёт, не изменяет и не удаляет чужие Secrets. Не выносить повторяемый жизненный цикл DB-init ресурсов обратно в consumer playbook.
- Keep deployment-specific values outside roles and pass them in explicitly from the consumer.
- Keep external dependencies declared in `requirements.yml`.
- Do not add environment-specific playbooks, inventory, or vault content here.
- For HomeLab consumers, controller-side kubeconfig sources must come only from
  the parent project's `kubeconfigs/`; never discover fallback credentials in
  controller `~/.kube/config` or `/etc/kubernetes/`. The explicitly permitted
  managed-host destination `{{ hermes_kubeconfig_user_home }}/.kube/config`
  is not a controller source. Keep selection and access generation in consumer
  playbooks, not the shared role.
- Preserve the kubeconfig role's credential handling: directory `0700`, file
  `0600`, selected user/group ownership, no credential logs or diffs, replacement
  without merge or backups. Do not install kubectl, alter environment overrides,
  generate credentials, call the Kubernetes API, or restart Hermes in this role.

## Validation

- Run checks from the repository root.
- Validate YAML with `yamllint`.
- Prefer `pdm run ansible-lint` for Ansible linting.

## How Agents Should Use This Map

1. Read this file first for repository boundaries.
2. Use `.agents/skills/ansible-role/SKILL.md` when creating or changing roles.
3. Keep changes minimal and aligned with the existing structure under `roles/`.
