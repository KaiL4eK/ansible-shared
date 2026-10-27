# PostgreSQL init database through Kubernetes Job

Создаёт отсутствующие login-role и database идемпотентной SQL-командой из
короткоживущего Kubernetes Job. PostgreSQL server не устанавливается: Job
подключается к заданному Service/DNS имени. Пин образа по умолчанию — официальный
`postgres:17.6-bookworm`.

Все параметры объявлены в `defaults/main.yml`. Режим по умолчанию использует
готовые Kubernetes Secrets (`k8s_postgresql_init_admin_secret_name` и
`k8s_postgresql_init_user_secret_name`) и не создаёт, не изменяет и не удаляет их.
Username администратора в этом режиме приходит либо ключом
`k8s_postgresql_init_admin_username_key` из готового Secret, либо inline через
`k8s_postgresql_init_admin_user` — по умолчанию оба входа пустые, потребитель
обязан задать ровно один. Inline
вариант рассчитан на штатные чарт-Secret'ы bitnami, где хранится только ключ
пароля (`postgres-password`), а администратор — `postgres`; пароль при этом
всё равно читается из Secret (`k8s_postgresql_init_admin_secret_key`) и не
попадает в Job spec.

При `k8s_postgresql_init_manage_credentials: true` плейбук передаёт
`k8s_postgresql_init_admin_user`, `k8s_postgresql_init_admin_password`,
`k8s_postgresql_init_user` и `k8s_postgresql_init_password` из своего Vault.
Роль сама проверяет входы и существование namespace, создаёт уникальный временный
Secret и Job, ждёт результат и удаляет Secret в `always`, в том числе при ошибке.
Параметр `k8s_postgresql_init_job_name` служит префиксом (до 34 символов);
фактическое имя генерируется сервером и уникально для каждого запуска.
Имена готовых Secrets в этом режиме передавать нельзя. Check mode отклоняется.
Необязательный `k8s_postgresql_init_kubeconfig` позволяет проверить наличие явно
выбранного файла без чтения; подключение использует стандартные `K8S_AUTH_*`.

Пароли Job получает через `secretKeyRef`; значения паролей не попадают в Job spec
или логи. Операции с Secret скрыты через `no_log: true`, `diff: false`.
Роль ждёт `Complete` или `Failed`, завершает play с ошибкой при неуспехе.
Job автоматически очищается TTL-контроллером через 10 минут, Pod не получает
ServiceAccount token.

Для режима готовых Secrets нужны права на Job и чтение его статуса. Для режима
credentials дополнительно нужны чтение namespace и создание/удаление Secrets.
Namespace должен существовать заранее. Secrets защищать namespace-scoped RBAC
и encryption at rest. DB-init запускает оператор, не application CI.
При принудительном завершении Ansible `always` не гарантирован: оставшийся
временный Secret удаляет оператор. ConfigMaps роль не создаёт.

Существующие пароль, атрибуты пользователя и владелец БД не изменяются.
Перед созданием БД Job проверяет вход с application credentials в
`k8s_postgresql_init_admin_database` (по умолчанию `postgres`). Ошибка входа или
конфликт владельца существующей БД завершает Job с ошибкой, без сброса пароля.
Должен быть разрешён CONNECT к проверочной БД и настроена парольная
аутентификация PostgreSQL: контрольный вход с заведомо неверным паролем обязан
завершаться ошибкой. `trust` и прочие способы входа без проверки пароля отклоняются.
Ротация credentials — отдельная операторская операция, не часть bootstrap.
