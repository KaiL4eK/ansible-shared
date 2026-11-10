# minio/mc-init-user-bucket

Инициализация S3-контура приложения на mc-admin-совместимом бэкенде (MinIO,
RustFS и другие реализации MinIO admin API): IAM-юзер приложения с политикой
и нужные бакеты — короткоживущими Kubernetes Job'ами с `mc` (scratch-образ;
публичный mc удалён из registry, официальный aws-cli требует x86-64-v2 —
образ публикуется consumer-проектом в собственный registry и передаётся
явно). Аналог `k8s/postgresql-init-db` для объектного хранилища.

## Контракт

Роль работает через MinIO admin API (`mc admin user add`, `mc admin policy
attach`, `mc mb`) — подойдёт любой бэкенд, реализующий этот API; произвольные
S3-провайдеры (AWS S3, Ceph RGW и т.п.) не поддерживаются.

Два режима источников кредов (стороны root и юзер независимы, гибрид
допустим):

- **Готовые Secret'ы**: имя Secret'а и имена ключей для каждой стороны
  (root-креды и креды юзера приложения, обычно контракт `S3_*`); имена
  ключей обязательны — дефолтов нет, у каждого чарта/проекции свои. Preflight
  ждёт наличие Secret'ов и непустые значения ключей. Значения не читаются,
  не печатаются и не попадают в определения Job (только `secretKeyRef` +
  placeholder'ы `$(VAR)`, которые раскрывает kubelet в env и args).
- **Inline-значения**: креды передаются переменными `*_value`; роль создаёт
  временный Secret с фиксированным именем `<job_name>-tmp-creds` (`no_log`;
  остаток прерванного прогона перезаписывается), запускает Job'ы через
  `secretKeyRef` на него и удаляет его в `always`. Для каждого источника —
  ровно один вход: имя Secret'а ИЛИ inline-значения (XOR, валидируется).

Секрет юзера приложения (`access key`/`secret key`): роль регистрирует их как
IAM-юзера (в mc access key — это и есть имя юзера), прикрепляет политику и
создаёт бакеты. Отдельного «имени юзера» нет. Алиас mc (`*_alias`) —
локальное имя подключения внутри Job'ов, на бэкенд не влияет.
Идемпотентность: повторный запуск безопасен (`user add` переустанавливает
секрет, `policy attach` уже прикреплённой политики — no-op,
`mb --ignore-existing`). Ротация пароля юзера — новое значение в источнике →
повторный запуск роли.

## Переменные (defaults)

| Переменная | Назначение |
| --- | --- |
| `minio_mc_init_namespace` | namespace, где создаются Job'ы и временный Secret |
| `minio_mc_init_job_name` | префикс Job'ов (`-user-add`, `-policy`, `-buckets`) и временного Secret'а (`-tmp-creds`), ≤ 30 символов |
| `minio_mc_init_labels` | лейблы Job'ов (задаются целиком) |
| `minio_mc_init_alias` | алиас mc внутри Job'ов (по умолчанию `s3`) |
| `minio_mc_init_mc_image` / `_mc_image_tag` | pinned scratch-образ mc (обязательны) |
| `minio_mc_init_endpoint` | in-cluster S3 endpoint (например `http://<svc>.<ns>.svc:9000`) |
| `minio_mc_init_root_secret_name` + ключи | root-креды бэкенда; ключи обязательны в этом режиме |
| `minio_mc_init_app_secret_name` + ключи | креды юзера приложения; ключи приложения дефолтятся в `S3_ACCESS_KEY`/`S3_SECRET_KEY` |
| `minio_mc_init_user_policy` | политика юзера (по умолчанию `readwrite`) |
| `minio_mc_init_buckets` | список бакетов |
| `minio_mc_init_timeout` | окно ожидания каждого Job'а, сек |
| `minio_mc_init_kubeconfig` | путь kubeconfig для модулей kubernetes.core |
| `minio_mc_init_root_access_key_value` + `minio_mc_init_root_secret_value` | inline root-креды |
| `minio_mc_init_app_access_key_value` + `minio_mc_init_app_secret_value` | inline креды юзера |

## Использование

Consumer playbook передаёт имя целевого namespace, pinned образ mc, endpoint
и источники кредов; проверка контракта — `ansible-playbook --syntax-check`.
Пример вызова:

```yaml
- name: Initialize the application S3 user and buckets
  ansible.builtin.include_role:
    name: minio/mc-init-user-bucket
  vars:
    minio_mc_init_namespace: "{{ app_namespace }}"
    minio_mc_init_job_name: app-s3-init
    minio_mc_init_mc_image: "<registry>/<project>/mc"
    minio_mc_init_mc_image_tag: "RELEASE.2025-08-13T08-35-41Z"
    minio_mc_init_endpoint: "http://<s3-svc>.<ns>.svc.cluster.local:9000"
    minio_mc_init_root_secret_name: "<root-credentials-secret>"
    minio_mc_init_root_access_key: "<root-access-key-name>"
    minio_mc_init_root_secret_key: "<root-secret-key-name>"
    minio_mc_init_app_secret_name: "<app-s3-secret>"
    minio_mc_init_buckets: ["<bucket>"]
    minio_mc_init_kubeconfig: "{{ kubeconfig_path }}"
```
