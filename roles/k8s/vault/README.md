# Vault с PostgreSQL backend

Роль устанавливает официальный `hashicorp/vault` chart 0.34.1 и Vault 2.2.0.
БД, пользователя и таблицы заранее создаёт вызывающий плейбук. Входы объявлены
в `defaults/main.yml`, префикс `k8s_vault_`. URL БД передаётся только через Secret
и `VAULT_PG_CONNECTION_URL`, не через Helm values/ConfigMap.

Один экземпляр, без dev mode, injector, CSI и PVC. PostgreSQL backend поддерживается
сообществом. TLS внутри кластера выключен; внешний TLS задаётся через
`ingress_tls`/`ingress_annotations`. Не использовать HTTP в недоверенной сети.

По умолчанию `wait: false`, `atomic: false`: новый сервер не Ready до ручных
init/unseal. Readiness сохраняет отказ для sealed/uninitialized, liveness
не перезапускает сервер из-за этих состояний. Init/unseal роль не выполняет.
После распечатки можно включить wait/atomic. Обновления StatefulSet — `OnDelete`:
оператор сам планирует замену pod и повторный unseal. Изменение Secret требует
ручного пересоздания pod, чтобы обновилось окружение процесса.
