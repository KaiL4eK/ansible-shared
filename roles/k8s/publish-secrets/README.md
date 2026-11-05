# Publish runtime Kubernetes Secrets from playbook-loaded credentials

Публикация runtime Secret'ов Kubernetes из значений, уже загруженных
вызывающим плейбуком (типовой источник — Ansible Vault через `vars_files`
или `include_vars`; роль источник не знает и credentials не читает сама).
Валидация значений и публикация выполняются под `no_log`; наружу — только
имена Secret'ов. Развёртывание кластера, Helm-релизы и ротация значений —
вне роли: повторный запуск перезаписывает Secret'ы переданными значениями
(`force: true`).

Все параметры объявлены в `defaults/main.yml`, префикс `k8s_publish_secrets_`.

## Входы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `k8s_publish_secrets_namespace` | (пусто) | Namespace публикации; consumer задаёт явно |
| `k8s_publish_secrets` | `{}` | `{имя Secret: {ключ: значение}}`, значения — строки |
| `k8s_publish_secrets_labels` | `managed-by: ansible` | Лейблы объектов; consumer добавляет свои |
| `k8s_publish_secrets_verify` | `true` | Сверка состава ключей после применения |
| `k8s_publish_secrets_verify_retries` / `_delay` | `6` / `5` | Ретраи верификации |

## Поведение

- preflight: непустые значения, без пустых строк, только строки,
  без значений-заглушек (`CHANGE_ME`/`dummy`/`placeholder`); проверки под
  `no_log` — провал не печатает значения;
- публикация `type: Opaque` с base64-кодировкой ключей и `force: true`
  (источник истины — переданный словарь);
- при провале публикации наружу выходит sanitized-сводка
  `имя | HTTP-код | reason | message API`: `message` — поле тела Status-ответа
  (причины вида invalid data key, immutable, admission), перед показом
  очищается от публикуемых значений и их base64-форм; полный вывод задачи
  остаётся под `no_log`;
- верификация: состав ключей каждого Secret сверяется с ожидаемым —
  только имена ключей, значения не читаются.

## Пример вызова

```yaml
- name: Publish app runtime secrets
  ansible.builtin.include_role:
    name: k8s/publish-secrets
  vars:
    k8s_publish_secrets_namespace: apps-stage
    k8s_publish_secrets: "{{ app_runtime_secrets }}"   # из env.yml + vault
```
