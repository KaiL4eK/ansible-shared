# Vault Secrets Operator

Устанавливает официальный `hashicorp/vault-secrets-operator` в существующий
namespace. Chart `1.6.0`, operator `1.6.1` и kube-rbac-proxy `v0.18.1`
зафиксированы отдельными входами `k8s_vso_*` в `defaults/main.yml`.

Namespace не создаётся; необходимы права на CRD и cluster RBAC. CRD upgrade hook
включён, `atomic` выключен: откат Helm не откатывает схему CRD. CSI выключен,
ingress/PVC не требуются, Vault-токены не сохраняются в Kubernetes client cache.
Общие default auth/connection не создаются: потребитель описывает свои
`VaultConnection`, `VaultAuth`, ServiceAccount и ресурсы синхронизации отдельно.

Чарт допускает Kubernetes >=1.21; это не означает upstream-поддержку всех старых
версий. Совместимость конкретного кластера и Vault проверяется при применении.
Обновление версии требует проверки values, CRD и итогового `helm template`.
