# VaultStaticSecret projection for an existing VSO consumer

Reconcile VaultStaticSecret-ресурсов на существующий VaultAuth-консьюмер
и верификация синхронизации destination Secret'ов. Консьюмер
(ServiceAccount/VaultConnection/VaultAuth), mount и Vault в роль не входят:
их создаёт отдельный bootstrap; кластерные модули используют kubeconfig из
environment плейбука (`K8S_AUTH_KUBECONFIG`/`KUBECONFIG`).

Все параметры объявлены в `defaults/main.yml`, префикс `k8s_vso_`.

## Входы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `k8s_vso_namespace` | (пусто) | Namespace проекции; consumer задаёт явно |
| `k8s_vso_auth_name` | `kv-agent` | vaultAuthRef — имя VaultAuth-консьюмера |
| `k8s_vso_mount` | `kv-agent` | Mount KV v2 в Vault |
| `k8s_vso_secrets` | `[]` | Список проекций (формат ниже) |
| `k8s_vso_check_crd` | `true` | Проверить установку CRD VSO |
| `k8s_vso_check_vault_auth` | `true` | Проверить существование VaultAuth |
| `k8s_vso_wait_timeout` | `300` | Ожидание condition `SecretSynced=True` (сек) |
| `k8s_vso_key_check_retries` / `_delay` | `10` / `5` | Ретраи сверки ключей destination |

Формат элемента `k8s_vso_secrets`:

```yaml
- name: my-app-database        # имя VaultStaticSecret
  path: services/apps-stage/my-app/database
  destination: my-app-database # имя destination Secret (по умолчанию = name)
  includes: ["^DATABASE_USER$", "^DATABASE_PASSWORD$"]  # контракт ключей
  keys: [DATABASE_USER, DATABASE_PASSWORD]              # ожидаемые ключи
  templates: {}                # Go-шаблоны VSO (опционально)
  restart_targets:             # rolloutRestartTargets (опционально)
    - kind: Deployment
      name: my-app
  refresh_after: 60s           # период синка VSO (опционально)
```

## Поведение

- preflight: входы, CRD VSO, существование VaultAuth в namespace;
- reconcile каждого VaultStaticSecret (`kv-v2`, `hmacSecretData: true`,
  `excludeRaw: true`, destination create/overwrite, includes из контракта);
- ожидание `SecretSynced=True` и сверка `status.lastGeneration` с
  `metadata.generation` (VSO отработал именно текущую спецификацию);
- сверка ожидаемых ключей в destination Secret — только имена ключей,
  значения не читаются и не печатаются (задача под `no_log`).

## Гарантии безопасности

- значения секретов роль не выводит; наружу — sanitized-summary
  (имена ресурсов, mount, VaultAuth);
- `includes` ограничивают ключи контрактом: случайные ключи Vault-пути
  в Secret не попадают.

## Пример вызова

```yaml
- name: Project app secrets
  ansible.builtin.include_role:
    name: k8s/vso-static-secret
  vars:
    k8s_vso_namespace: apps-stage
    k8s_vso_secrets:
      - name: my-app-database
        path: services/apps-stage/my-app/database
        includes: ["^DATABASE_USER$", "^DATABASE_PASSWORD$"]
        keys: [DATABASE_USER, DATABASE_PASSWORD]
```
