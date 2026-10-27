# PostgreSQL schema through Kubernetes Job

Применяет идемпотентные SQL-выражения (схема приложения) короткоживущим
Kubernetes Job. PostgreSQL server не устанавливается: Job подключается к
заданному Service/DNS имени под учёткой приложения. Пин образа по умолчанию —
официальный `postgres:17.6-bookworm`.

Все параметры объявлены в `defaults/main.yml`, префикс `k8s_postgresql_schema_`.
Идентичность Job'а — в одном из двух режимов: managed (по умолчанию) с inline
`user`/`password` через уникальный временный Secret, либо режим готовых
Secret'ов — `user_secret_name` + `user_secret_key`, username ключом
`user_username_key` или инлайном `user` (XOR, как admin-входы
`k8/postgresql-init-db`); в этом режиме пароль всегда через `secretKeyRef`,
а временный Secret не создаётся, если нет inline-значений в `secret_env`.
Роль сама делает preflight переданных готовых Secret'ов: ожидает наличие,
ключи и непустые значения (`k8s_postgresql_schema_secret_preflight_retries`,
12 × 5s) — consumer playbook не ждёт секреты и не знает их источник.
Проверяется существование namespace; check mode отклоняется.
`k8s_postgresql_schema_job_name` служит префиксом (до 34 символов);
уникальность имени конкретного запуска Job'а обеспечивает суффикс с меткой
времени. Необязательный `k8s_postgresql_schema_kubeconfig` позволяет
проверить наличие явно выбранного файла без чтения; подключение использует
стандартные `K8S_AUTH_*`.

Пароль Job получает через `secretKeyRef`; значения не попадают в Job spec или
логи (исключение — инлайн username в режиме готовых Secret'ов, как
`k8s_postgresql_init_admin_user` в `k8s/postgresql-init-db`). SQL-выражения
передаются списком `k8s_postgresql_schema_statements` и склеиваются построчно
в один `psql`-скрипт с `ON_ERROR_STOP`; ошибки SQL завершают Job с ошибкой.
Каждое SQL-выражение потребитель завершает собственным `;` (psql исполняет
буфер на `;`); выражение, питающее следующую meta-команду (`\gexec`), идёт
без `;`. Допускаются psql meta-команды (`\getenv`, `\gexec`) как отдельные
элементы списка; `\getenv` требует psql >= 15 (пин образа 17.6 этому
удовлетворяет). Выражения не являются секретом и видны в Job spec;
секретные значения передаются через `k8s_postgresql_schema_secret_env`:
запись `{name: ENV_NAME, value}` идёт через временный Secret, запись
`{name, secret_name, secret_key}` — прямым `secretKeyRef` в готовый Secret;
SQL читает их через `\getenv`.
Для идемпотентных повторных запусков выражения должны использовать
`CREATE ... IF NOT EXISTS`; расхождения существующей схемы роль не выправляет.

Операции с Secret скрыты через `no_log: true`, `diff: false`. Роль ждёт
`Complete` или `Failed` и завершает play с ошибкой при неуспехе. Job
автоматически очищается TTL-контроллером через 10 минут, Pod не получает
ServiceAccount token. Нужны права на Job и чтение его статуса, а также
создание/удаление Secrets в целевом namespace. Пользователь должен иметь право
создавать объекты в целевой схеме (обычно — owner БД, как выдаёт
`k8s/postgresql-init-db`).
