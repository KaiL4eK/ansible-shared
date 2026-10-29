# PostgreSQL init database through Kubernetes Job

Создаёт отсутствующие login-role и database идемпотентной SQL-командой из
короткоживущего Kubernetes Job. PostgreSQL server не устанавливается: Job
подключается к заданному Service/DNS имени. Пин образа по умолчанию — официальный
`postgres:17.6-bookworm`.

## Режимы

Переключатель — `k8s_postgresql_init_manage_credentials` (по умолчанию `false`).
Источники credentials по режимам:

| Режим | Пароль администратора | Креды юзера | Временный Secret |
| --- | --- | --- | --- |
| Готовые Secrets (default) | готовый Secret | готовый Secret | не создаётся |
| Managed, inline-админ | Vault → плейбук | Vault → плейбук | оба набора |
| Managed, гибрид | готовый Secret (bitnami-чарт) | Vault → плейбук | только креды юзера |

Ровно один источник пароля администратора: inline
`k8s_postgresql_init_admin_password` XOR готовый
`k8s_postgresql_init_admin_secret_name` — контракт проверяется assert'ом.

## Настройка

Общие входы для всех режимов (полный список — `defaults/main.yml`):
`k8s_postgresql_init_namespace` (обязателен, должен существовать),
`k8s_postgresql_init_job_name` (префикс имени Job'а, до 34 символов; фактическое
имя генерируется сервером и уникально для каждого запуска),
`k8s_postgresql_init_host`/`_port`/`_sslmode`, целевая
`k8s_postgresql_init_database`, проверочная `k8s_postgresql_init_admin_database`
(по умолчанию `postgres`), `k8s_postgresql_init_timeout` и необязательный
`k8s_postgresql_init_kubeconfig` (проверяет наличие выбранного файла без чтения;
подключение использует стандартные `K8S_AUTH_*`).

Username администратора везде приходит либо ключом
`k8s_postgresql_init_admin_username_key` из соответствующего Secret, либо inline
через `k8s_postgresql_init_admin_user` — ровно один из двух входов. Inline
вариант рассчитан на штатные чарт-Secret'ы bitnami, где хранится только ключ
пароля (`postgres-password`), а администратор — `postgres`.

### Режим готовых Secrets (по умолчанию)

Плейбук передаёт только имена готовых Secret'ов и их ключи и не знает их
источник (чарт/VSO). Роль не создаёт, не изменяет и не удаляет чужие Secret'ы;
preflight сам ждёт наличие, ключи и непустые значения
(`k8s_postgresql_init_secret_preflight_retries`, 12 × 5s).

```yaml
roles:
  - role: k8s/postgresql-init-db
    vars:
      k8s_postgresql_init_namespace: apps
      k8s_postgresql_init_job_name: mot-db-init
      k8s_postgresql_init_host: bifrost-logs-postgresql.apps.svc.cluster.local
      k8s_postgresql_init_database: mot_logs
      # Админ: чарт-Secret bitnami — username inline, пароль ключом Secret'а.
      k8s_postgresql_init_admin_secret_name: bifrost-logs-postgresql
      k8s_postgresql_init_admin_secret_key: postgres-password
      k8s_postgresql_init_admin_user: postgres
      # Юзер: runtime-Secret приложения.
      k8s_postgresql_init_user_secret_name: ministry-of-tokens-database
      k8s_postgresql_init_user_username_key: MOT_DATABASE_USERNAME
      k8s_postgresql_init_user_secret_key: MOT_DATABASE_PASSWORD
```

### Managed-режим: inline-пароль администратора

`k8s_postgresql_init_manage_credentials: true`. Креды обоих наборов приходят
из Vault потребителя; роль валидирует входы, создаёт уникальный временный
Secret с обоими наборами, запускает Job и удаляет Secret в `always`, в том
числе при ошибке (`no_log: true`, `diff: false`). Имена готовых Secret'ов
передавать нельзя. Check mode отклоняется.

```yaml
roles:
  - role: k8s/postgresql-init-db
    vars:
      k8s_postgresql_init_manage_credentials: true
      k8s_postgresql_init_namespace: apps
      k8s_postgresql_init_job_name: bifrost-db-init
      k8s_postgresql_init_host: postgresql.service.svc.cluster.local
      k8s_postgresql_init_database: bifrost-llm-proxy
      k8s_postgresql_init_admin_user: postgres
      k8s_postgresql_init_admin_password: "{{ service_db_postgres_admin_password }}"
      k8s_postgresql_init_user: bifrost-llm-proxy
      k8s_postgresql_init_password: "{{ bifrost_postgres_password }}"
```

### Managed-режим: гибрид с внешним админ-Secret'ом

Тот же переключатель, но вместо inline-пароля администратора — ссылка на
готовый Secret (типовой случай: пароль уже лежит в чарт-Secret релиза
bitnami PostgreSQL, который создал деплой-плейбук). Роль preflight'ит внешний
Secret так же, как в режиме готовых Secrets, временный Secret создаётся только
под креды юзера: значение админ-Secret'а не копируется, Job получает его через
`secretKeyRef`. Имя готового user-Secret'а передавать нельзя — креды юзера
только role-managed.

```yaml
roles:
  - role: k8s/postgresql-init-db
    vars:
      k8s_postgresql_init_manage_credentials: true
      k8s_postgresql_init_namespace: apps
      k8s_postgresql_init_job_name: bifrost-logs-db-init
      k8s_postgresql_init_host: bifrost-logs-postgresql.apps.svc.cluster.local
      k8s_postgresql_init_database: bifrost_logs
      # Админ — из чарт-Secret релиза, username inline (в чарт-Secret bitnami
      # ключа username нет).
      k8s_postgresql_init_admin_secret_name: bifrost-logs-postgresql
      k8s_postgresql_init_admin_secret_key: postgres-password
      k8s_postgresql_init_admin_user: postgres
      # Юзер — role-managed из Vault.
      k8s_postgresql_init_user: bifrost_logs
      k8s_postgresql_init_password: "{{ bifrost_logs_postgres_password }}"
```

Источник истины пароля в гибриде остаётся один: Vault → Helm values
деплоя-плейбука → чарт-Secret, из которого init его читает.

## Поведение и гарантии

- Пароли Job получает только через `secretKeyRef`; значения паролей не
  попадают в Job spec или логи. Операции с Secret скрыты через
  `no_log: true`, `diff: false`; preflight проверяет наличие, ключи и
  непустые значения, не раскрывая содержимое.
- Роль ждёт `Complete` или `Failed`, завершает play с ошибкой при неуспехе.
  Job автоматически очищается TTL-контроллером через 10 минут, Pod не
  получает ServiceAccount token. ConfigMaps роль не создаёт.
- Существующие пароль, атрибуты пользователя и владелец БД не изменяются.
  Перед созданием БД Job проверяет вход с application credentials в
  `k8s_postgresql_init_admin_database`. Ошибка входа или конфликт владельца
  существующей БД завершает Job с ошибкой, без сброса пароля. Должен быть
  разрешён CONNECT к проверочной БД и настроена парольная аутентификация
  PostgreSQL: контрольный вход с заведомо неверным паролем обязан завершаться
  ошибкой. `trust` и прочие способы входа без проверки пароля отклоняются.
  Ротация credentials — отдельная операторская операция, не часть bootstrap.
- RBAC: для режима готовых Secrets нужны права на Job и чтение его статуса.
  Для managed-режима дополнительно нужны чтение namespace и
  создание/удаление Secrets (секреты резолвит kubelet, SA токен поду не
  выдаётся). Secrets защищать namespace-scoped RBAC и encryption at rest.
  DB-init запускает оператор, не application CI. При принудительном
  завершении Ansible `always` не гарантирован: оставшийся временный Secret
  удаляет оператор.
