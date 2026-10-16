# Общие роли мониторинга

Роли не устанавливают стек мониторинга и не читают inventory, vault или kubeconfig
по неявным путям. Потребитель задаёт авторизацию Kubernetes через окружение
`K8S_AUTH_KUBECONFIG`/`KUBECONFIG` своего playbook. Нужны `kubernetes.core`
из `requirements.yml` и Python-пакет `kubernetes` на контроллере.

## `k8s/monitoring/grafana-dashboard`

Входы: `grafana_dashboard_files` — непустой список путей к JSON на контроллере,
`grafana_dashboard_namespace` — namespace Grafana (по умолчанию `monitoring`).
Файлы должны иметь уникальные нормализованные имена во всех папках.

Создаёт `grafana-dashboard-<basename без расширения, lower, _ → ->`, сохраняя
JSON, UID и datasource без изменений. Имя родительской директории становится
аннотацией `grafana_folder`. Метки задаёт `grafana_dashboard_configmap_labels`
(по умолчанию `grafana_dashboard: "1"` и `app.kubernetes.io/managed-by: ansible`).
В Grafana нужен sidecar с `folderAnnotation: grafana_folder` и
`provider.foldersFromFilesStructure: true`.

API Grafana не вызывается: папки создаёт provisioning по аннотации
`grafana_folder`. Роль не принимает admin credentials и не требует Grafana vault.

```yaml
- name: Добавить дашборд
  ansible.builtin.include_role:
    name: k8s/monitoring/grafana-dashboard
  vars:
    grafana_dashboard_namespace: monitoring
    grafana_dashboard_files:
      - "{{ playbook_dir }}/../definitions/ML Servers/vllm.json"
```

## `k8s/monitoring/prometheus-rule`

Вход `prometheus_rule_definitions` — непустой список готовых документов
`monitoring.coreos.com/v1`, `kind: PrometheusRule`. Каждый документ задаёт
`metadata.name`, `metadata.namespace`, labels селектора Prometheus и `spec.groups`.
Поддерживает и alert rules, и recording rules. Документы применяются без
изменения меток, выражений, порогов и маршрутизации.

```yaml
- name: Добавить алерты
  ansible.builtin.include_role:
    name: k8s/monitoring/prometheus-rule
  vars:
    prometheus_rule_definitions: "{{ [lookup('template', playbook_dir ~ '/templates/service.yaml.j2') | from_yaml] }}"
```

Каналы и receiver'ы Alertmanager настраиваются отдельно. При opt-in маршрутизации
каждое alert-правило должно иметь `labels.channel`, иначе оно уйдёт в receiver
по умолчанию. Роль не изменяет Secret Alertmanager или Helm-релиз стека.

Роли управляют только переданными ресурсами; удаление определения из репозитория
не удаляет существующий ConfigMap/PrometheusRule из кластера.
