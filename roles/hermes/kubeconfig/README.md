# Hermes Kubeconfig

Installs an explicitly selected controller-side kubeconfig at
`{{ hermes_kubeconfig_user_home }}/.kube/config`. The caller supplies privilege
escalation and an existing user. No cluster credentials are generated and no
Kubernetes API requests are made by this role.

| Input | Default | Meaning |
| --- | --- | --- |
| `hermes_kubeconfig_source` | empty, required | Absolute controller-side filename |
| `hermes_kubeconfig_user` | `hermes` | Existing destination owner |
| `hermes_kubeconfig_group` | user name | Existing destination group |
| `hermes_kubeconfig_user_home` | `/home/<user>` | Runtime user's home |

The directory is `0700` and the file is `0600`. Copying is atomic and idempotent;
the file replaces rather than merges an existing kubeconfig. No backup copy of
credentials is created. Credentials are excluded from logs and diffs.

Kubernetes clients use this default location when `HOME` points to the user's
home and no `KUBECONFIG` or explicit client configuration overrides it. The role
does not install kubectl, change Hermes environment variables, or restart it.
