# Vault с PostgreSQL backend

Роль устанавливает официальный `hashicorp/vault` chart 0.34.1 и Vault 2.2.0.
БД, пользователя и таблицы заранее создаёт вызывающий плейбук. Входы объявлены
в `defaults/main.yml`, префикс `k8s_vault_`. URL БД передаётся только через Secret
и `VAULT_PG_CONNECTION_URL`, не через Helm values/ConfigMap.

Один экземпляр, без dev mode, injector, CSI и PVC. PostgreSQL backend поддерживается
сообществом. TLS внутри кластера выключен; внешний TLS задаётся через
`ingress_tls`/`ingress_annotations`. Не использовать HTTP в недоверенной сети.

## Автоматический init/unseal

При `k8s_vault_unseal_enabled: true` роль после Helm:

1. ждёт Running pod сервера и проверяет состояние (`vault status`);
2. при первом запуске выполняет `vault operator init`
   (`k8s_vault_unseal_key_shares`/`k8s_vault_unseal_key_threshold`) и сохраняет
   unseal ключи (`unseal-key-N`, base64) и initial root token (`root-token`)
   в Secret `k8s_vault_unseal_secret_name`;
3. при последующих запусках распечатывает уже инициализированный Vault
   ключами из того же Secret.

StatefulSet монтирует Secret с ключами как volume, поэтому пустой Secret
создаётся **до** Helm (только при отсутствии, без перезаписи): иначе pod
зависает в ContainerCreating с FailedMount, а init выполняется лишь после
запуска pod.

Sidecar-контейнер `unsealer` (тот же образ Vault) монтирует Secret и после
любого рестарта pod сам подаёт ключи — ручной unseal не требуется.
Root token задаётся Vault'ом сам: своего значения указать нельзя.
Init/unseal-задачи выполняются через `kubectl exec` в контейнер `unsealer`
с явным `--kubeconfig` (переменная `k8s_vault_kubeconfig`, обязательна при
включённом авто-unseal; kubectl должен быть на контроллере). Путь принимается
в любой форме (`~`, `$VARS`, относительный) — роль нормализует его сама.
От `k8s_exec` отказались: у python-клиента kubernetes (websocket exec) известны
зависания и ошибки стрима, а env-прокидывание kubeconfig в command-задачи
оказалось ненадёжным. Задачи с ключами выполняются под `no_log`.

Компромисс безопасности: доступ на чтение Secret в namespace Vault позволяет
распечатать Vault. Для лабораторного окружения это осознанное решение (ADR-51
инфраструктурного репозитория). Ключи и токен не попадают в Helm values, логи
или репозиторий; все секретные задачи выполняются с `no_log`.

По умолчанию `wait: false`, `atomic: false`: init выполняется задачами роли
после Helm, поэтому pod не Ready во время установки. После успешного прогона
можно включить wait/atomic. Readiness сохраняет отказ для sealed/uninitialized,
liveness не перезапускает сервер из-за этих состояний. Изменения StatefulSet —
`OnDelete`: после замены pod unsealer распечатывает Vault автоматически.
Secret с ключами при инициализированном Vault не перезаписывается; если Vault
инициализирован, а Secret отсутствует, роль падает с инструкцией импорта ключей.
