# k8s/rustfs

Установка и обновление RustFS (S3-совместимое хранилище, совместимое с
`mc admin`) в Kubernetes через upstream Helm chart с пином версии chart и
образов. Роль ничего не знает об окружении consumer'а: namespace, креды,
размеры PVC и хосты ingress передаются явно.

## Контракт

- Релиз: `k8s_rustfs_namespace` (обязателен; namespace создаёт consumer —
  `create_namespace` по умолчанию выключен), `k8s_rustfs_release_name`,
  `k8s_rustfs_chart_ref/_repository_name/_repository_url/_chart_version`
  (дефолты — официальный repo `https://charts.rustfs.com`, chart `1.0.4`).
- Образы: `k8s_rustfs_image_values` / `k8s_rustfs_init_image_values`.
  Образ RustFS пинится той же версией, что и chart (требование README
  chart'а); `initImage` — любой busybox (init-контейнер mkdir/chmod).
- Root-credentials: `k8s_rustfs_credentials_source`
  - `values` — consumer передаёт `k8s_rustfs_access_key` / `_secret_key`
    явно (типовой источник — Ansible Vault в consumer playbook);
  - `generated` — роль обеспечивает админ-секрет сама: при наличии в
    кластере Secret'а чарта `<fullname>-secret` переиспользует его значения
    (идемпотентность, без ротации), иначе генерирует случайные
    (`k8s_rustfs_generated_*_length`). Значения live в Secret релиза.
  Well-known `rustfsadmin` и пустые значения отклоняются (guard чарта).
  Задача Helm выполняется с `no_log` — креды не попадают в логи.
- Топология `k8s_rustfs_mode`:
  - `standalone` — Deployment (`replicaCount`), PVC `<release>-data` и
    `<release>-logs`;
  - `distributed` — StatefulSet erasure-coded кластер, чарт требует
    `replicaCount >= 2`; `k8s_rustfs_drives_per_node` и размеры/класс PVC
    задавать только до первой установки (`volumeClaimTemplates` иммутабельны).
- Хранилище: `k8s_rustfs_storage_class`, `k8s_rustfs_data_storage_size`,
  `k8s_rustfs_log_storage_size`; PVC создаются с аннотацией
  `helm.sh/resource-policy: keep` — переживают `helm delete`.
- Сервис и ingress: `k8s_rustfs_service_type`, порты endpoint/console;
  при `k8s_rustfs_ingress_enabled: true` обязательны оба хоста
  (`_api_host`, `_console_host`) — чарт рендерит один Ingress с двумя
  записями; TLS терминировать на ingress (`ingress.tls` чарта остаётся
  выключенным).
- Конфигурация: `k8s_rustfs_config` (passthrough в `config.rustfs` чарта —
  region, log_level, console_enable, domains и т.д.), `extra_env`,
  `resources`.
- Поведение Helm: `atomic`, `wait`, `take_ownership`, `timeout`.

## Интеграция с minio/mc-init-user-bucket

App-юзера и бакеты заводит соседняя роль
[`minio/mc-init-user-bucket`](../minio/mc-init-user-bucket/README.md):
root-credentials она берёт из Secret'а этого релиза (режим `generated`) или
из готового Secret consumer'а.

## Пример consumer playbook

```yaml
- name: Deploy RustFS
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: Install RustFS release
      ansible.builtin.include_role:
        name: k8s/rustfs
      vars:
        k8s_rustfs_namespace: storage
        k8s_rustfs_credentials_source: values
        k8s_rustfs_access_key: "{{ vault_rustfs_access_key }}"
        k8s_rustfs_secret_key: "{{ vault_rustfs_secret_key }}"
        k8s_rustfs_storage_class: local-path
        k8s_rustfs_data_storage_size: 20Gi
        k8s_rustfs_log_storage_size: 2Gi
```
