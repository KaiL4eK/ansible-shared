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

- Runtime-устанавливаемые в job-скриптах CLI-инструменты проверять по
  каноническому имени с fallback на имя дистрибутива: дистрибутивы
  переименовывают бинарники (пример: alpine `minio-client` ставит `mcli`, а
  не `mc`). После установки пакета создавать compatibility-symlink на
  каноничное имя (`ln -sf "$(command -v mcli)" /usr/local/bin/mc`) до
  `command -v`-проверки; сообщение об ошибке должно называть оба имени.
  Тестировать такие скрипты с абсолютными PATH — относительный PATH в
  локальных тестах создаёт битые symlink-и и даёт ложные результаты.

- PostgreSQL bootstrap (напрямую и через Kubernetes Job) создаёт только
  отсутствующие user/DB. Никогда не менять пароль/атрибуты существующего
  пользователя или владельца существующей БД. До создания БД проверять
  application credentials; при ошибке падать, не исправлять пароль.
  Успешный вход без парольной аутентификации не подтверждает совпадение пароля:
  контрольный вход с неверным паролем должен отклоняться. Проверять оба пути
  интеграционными тестами с сохранением исходного хеша пароля.

- Jinja2 не интерпретирует escape-последовательности в строковых литералах
  выражений: `join('\n')` даёт литеральный `\n`, а не перевод строки. Для
  реальных переводов строк использовать фолдед-скаляры YAML, переменные с
  двойными кавычками в YAML (`joiner: "\n"`) или структуру без переводов
  строк. Рендер сложных блоков (Job args, heredoc) проверять локальным
  рендер-тестом до деплоя.
- Булевы валидации состояний в `assert` проверять на всех комбинациях
  значений до деплоя: условие `a or not b` вместо `a or b` отклоняет валидную
  комбинацию и пропускает невалидную (кейс `k8s/vault`, инцидент
  2026-10-26). fail_msg делать динамическим, с фактическими значениями, —
  статичный текст про ожидаемую ошибку маскирует реальное состояние при
  диагностике. Парсер вывода внешнего CLI писать по формату, проверенному
  на реальной версии инструмента (docker run + команда): поля CLI и API
  различаются (`unseal_keys_b64` у `vault operator init -format=json`
  против `keys` у API `/sys/init`).

- Дашборды Grafana доставляются только через ConfigMap/sidecar; папки создаёт
  provisioning по `grafana_folder`. Не добавлять в роль дашбордов API Grafana,
  admin user/password или зависимость от Grafana vault.
- Use this file for repository-level rules and use `.agents/skills/ansible-role/SKILL.md` for role authoring workflow.
- Treat `roles/<domain>/<role-name>` as the standard role layout in this repository.
- Кластерный PostgreSQL bootstrap выполняет `roles/k8s/postgresql-init-db`: плейбук передаёт credentials и настройки, роль валидирует входы, в режиме готовых Secret'ов сама ждёт их наличие, ключи и непустые значения (`k8s_postgresql_init_secret_preflight_retries`), создаёт уникальный временный Secret, запускает Job и удаляет Secret в `always` (`no_log: true`, `diff: false`). Credentials Job получает только через `secretKeyRef`, не через args, SQL или ConfigMap. Сохранять совместимость режима готовых Secrets: в нём роль не создаёт, не изменяет и не удаляет чужие Secrets. Не выносить повторяемый жизненный цикл DB-init ресурсов обратно в consumer playbook.
- Имена ролей внутри домена пишутся через дефис (`k8s/postgresql-init-db`, `k8s/postgresql-schema`), не через подчёркивание. Если контракта роли не хватает consumer'у (пример — секретные значения в SQL через psql `\getenv`), расширять роль (у `k8s/postgresql-schema` — `k8s_postgresql_schema_secret_env`), а не дублировать Job-оркестрацию в плейбуке.
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
