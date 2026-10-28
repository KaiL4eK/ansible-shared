# KV v2 records in HashiCorp Vault via AppRole

Идемпотентный reconcile записей KV v2 в заданном mount: AppRole-логин,
чтение текущих версий, вычисление желаемого значения по каждому полю и
CAS-запись изменившихся записей. Роль работает только с Vault API с
контроллера: сервер Vault не разворачивает, Kubernetes Secret'ы не создаёт
и не читает, кластер не нужен.

Все параметры объявлены в `defaults/main.yml`, префикс `k8s_vault_kv_`.

## Входы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `k8s_vault_kv_address` | env `VAULT_ADDR` | Адрес Vault без `/v1`; HTTPS (HTTP — только loopback) |
| `k8s_vault_kv_role_id` | env `VAULT_ROLE_ID` | AppRole role_id (не секрет) |
| `k8s_vault_kv_secret_id` | env `VAULT_SECRET_ID` | AppRole secret_id (секрет) |
| `k8s_vault_kv_mount` | `secret` | Имя mount KV v2; consumer передаёт явно |
| `k8s_vault_kv_records` | `[]` | Список записей (формат ниже) |
| `k8s_vault_kv_default_length` | `32` | Длина генерируемых значений |
| `k8s_vault_kv_default_special` | `false` | Спецсимволы в генерируемых значениях |

Формат записи: `path` — путь без префикса mount, `fields` — словарь
`{имя_поля: spec}`; spec допускает ключи `length`, `special`, `rotate`,
`keep_existing`, `value` (валидацию конкретных ключей ведёт вызывающий
плейбук — роль проверяет только общие инварианты входов).

## Поведение

- существующие значения сохраняются (`keep_existing: true` по умолчанию);
- отсутствующие поля генерируются (`community.general.random_string`);
- `rotate: true` принудительно заменяет значение новым сгенерированным;
- `value` — литеральное значение (не генерируется и не ротируется);
- записываются только изменившиеся записи, с compare-and-set по текущей
  версии (конкурентная запись отклоняется, а не перетирает);
- временный AppRole-токен ревокается в `always`.

## Гарантии безопасности

- всё, что содержит значения или токены, — под `no_log: true`, `diff: false`;
- наружу — только sanitized-статусы и summary; результат для вызывающего
  плейбука — fact `k8s_vault_kv_summary` (`[{path, action, changed_fields}]`);
- registered-результаты с токенами не подаются напрямую в `assert`/`debug` —
  сначала сводятся к безопасным полям;
- policy AppRole должна разрешать `auth/token/revoke-self` и
  `auth/token/renew-self` (без них финальный ревок падает 403).

## Проверки входов

Preflight выполняется под `no_log` с boolean-результатами (формат адреса,
формат role_id, непустота secret_id, наличие записей); провал — `assert`
со скрытым значением и статическим именем непройденной проверки.

## Пример вызова

```yaml
- name: Reconcile records
  ansible.builtin.include_role:
    name: k8s/vault-kv
  vars:
    k8s_vault_kv_mount: kv-agent
    k8s_vault_kv_records:
      - path: services/apps-stage/demo/users
        fields:
          admin_password: {length: 32}
          api_key: {rotate: true}
          realm: {value: apps-stage}
```
