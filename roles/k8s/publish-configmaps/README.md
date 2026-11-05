# Publish open infrastructure ConfigMaps

Публикация открытых (некреденциальных) ConfigMap Kubernetes из переменных
вызывающего плейбука — типовой источник `<env>/env.yml`. Credentials в
ConfigMap не класть: секретные значения идут через runtime Secret'ы
(см. соседнюю роль `k8s/publish-secrets`). Валидация значений видимая —
значения не секретные.

Все параметры объявлены в `defaults/main.yml`, префикс `k8s_publish_configmaps_`.

## Входы

| Переменная | По умолчанию | Описание |
| --- | --- | --- |
| `k8s_publish_configmaps_namespace` | (пусто) | Namespace публикации; consumer задаёт явно |
| `k8s_publish_configmaps` | `{}` | `{имя ConfigMap: {ключ: значение}}`, значения — строки |
| `k8s_publish_configmaps_labels` | `managed-by: ansible` | Лейблы объектов; consumer добавляет свои |

## Поведение

- preflight: непустые значения, без пустых строк, только строки;
- публикация с `force: true` — переданный словарь является полным
  содержимым (перенесённые в чарт/приложение ключи из ConfigMap удаляются).

## Пример вызова

```yaml
- name: Publish app infrastructure configmaps
  ansible.builtin.include_role:
    name: k8s/publish-configmaps
  vars:
    k8s_publish_configmaps_namespace: "{{ app_namespace }}"
    k8s_publish_configmaps: "{{ app_runtime_configmaps }}"   # из env.yml
```
