# `k8s/helm-ci-kubeconfig`

Creates a namespace-scoped CI ServiceAccount, Role and RoleBinding, then writes
a standalone kubeconfig using a controller-populated ServiceAccount token Secret.
The selected namespace must already exist. The role does not create namespaces,
ClusterRoles, ClusterRoleBindings, or permissions for custom resources.

The source identity must be authorized to read the namespace and reconcile the
ServiceAccount, Role, RoleBinding and token Secret in it. Kubernetes RBAC
escalation checks still apply to the operator creating the RoleBinding.

## Inputs

All inputs use the `k8s_helm_ci_` prefix:

| Variable | Default | Purpose |
| --- | --- | --- |
| `k8s_helm_ci_name` | required | ServiceAccount and kubeconfig identity; DNS label, at most 57 characters |
| `k8s_helm_ci_namespace` | required | Existing target namespace |
| `k8s_helm_ci_source_kubeconfig` | required | Explicit controller-side authorized source; HTTPS and embedded CA required |
| `k8s_helm_ci_output_path` | required | Absolute controller-side kubeconfig path, distinct from source |
| `k8s_helm_ci_automount_service_account_token` | `false` | Keep CI identity's token from being mounted into Pods |
| `k8s_helm_ci_manage_serviceaccounts` | `true` | CRUD ServiceAccounts for charts; no `serviceaccounts/token` permission |
| `k8s_helm_ci_manage_statefulsets` | `false` | CRUD StatefulSets |
| `k8s_helm_ci_manage_daemonsets` | `false` | CRUD DaemonSets |
| `k8s_helm_ci_manage_cronjobs` | `false` | CRUD CronJobs |
| `k8s_helm_ci_manage_persistentvolumeclaims` | `false` | CRUD PVCs; consider data deletion implications |
| `k8s_helm_ci_manage_horizontalpodautoscalers` | `false` | CRUD HPAs |
| `k8s_helm_ci_manage_poddisruptionbudgets` | `false` | CRUD PDBs |
| `k8s_helm_ci_manage_networkpolicies` | `false` | CRUD NetworkPolicies |
| `k8s_helm_ci_token_retries` / `k8s_helm_ci_token_delay` | `30` / `2` | Bounded wait for the token controller |

The default profile grants full Helm lifecycle verbs on ConfigMaps, Secrets,
Services, Deployments, Jobs and Ingresses; reads Pods and ReplicaSets for
readiness checks; and manages ServiceAccounts for common charts. Optional
resource types are added only when enabled. It never grants RBAC, exec,
port-forward, namespace, cluster-scoped, or wildcard permissions.

Helm's default Secret storage driver requires read/write access to all Secrets
in the namespace. Kubernetes RBAC cannot restrict top-level Secret creation by
resource name, and workload writes can indirectly access other namespace
Secrets. Treat the namespace as the security boundary and avoid sharing it with
untrusted workloads.

The token Secret and kubeconfig contain credentials. Secret reads/creation and
kubeconfig rendering/writing are hidden from logs and diffs. The output directory
is mode `0700`, and the output file is mode `0600`. Re-runs preserve the issued
token. Rotate by revoking the existing ServiceAccount/token Secret and rerunning;
revoke access by removing the RoleBinding or ServiceAccount and deleting the
generated CI secret. The file itself is not uploaded to a CI provider.

Run the synthetic template/RBAC test without cluster access from the parent
`ansible/` directory with
`pdm run ansible-playbook ansible-shared/tests/helm-ci-kubeconfig.yml`.
