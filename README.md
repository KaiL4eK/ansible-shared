# ansible-shared

Reusable Ansible roles for shared automation.

## Purpose

`ansible-shared` is a small library of reusable Ansible roles that can be consumed from different playbook collections.

This repository should contain generic role logic, not environment-specific inventory, vault content, or orchestration glue.

## Structure

- `roles/` contains shared roles grouped by domain using `roles/<domain>/<role-name>`.
- `.agents/skills/` contains local skills for implementing and reviewing shared roles.
- `requirements.yml` defines external role and collection dependencies for this repository.
- `AGENTS.md` contains local development rules.
- `LICENSE` defines reuse terms for this repository.

## Preparation

Before working with this repository, install Ansible dependencies:

`ansible-galaxy collection install -r requirements.yml`

## Local Skills

- `.agents/skills/ansible-role/SKILL.md` describes how to create and refine roles in this repository.

## Current Content

- `roles/postgresql/init-db/` — прямое создание отсутствующих PostgreSQL user/DB;
  существующий пароль не меняется, ошибка проверки credentials останавливает
  bootstrap. Такой же контракт у `roles/k8s/postgresql_init_db/`.

- `roles/k8s/vault/` — Vault с внешним PostgreSQL backend, credentials через
  Secret, ручные init/unseal; [контракт роли](roles/k8s/vault/README.md).

- `roles/k8s/bifrost-llm-proxy/` — Bifrost через официальный Helm chart.
  Credentials передаются непосредственно через Helm values; отдельный Secret
  роль не создаёт. Helm values формируются непосредственно из переменных роли,
  без промежуточных facts и словарей overrides. Входы с префиксом
  `bifrost_llm_proxy_`: `encryption_key`, `auth_*`, `enforce_auth_on_inference`,
  `enable_logging`, `disable_content_logging`, `vk_rotation_cooldown`,
  `config_store_enabled`, `config_store_type`, `logs_store_enabled`,
  `logs_store_type` и `persistence_*`. Auth доставляется через
  `bifrost.governance.authConfig`, persistence — через `storage.persistence`
  по структуре chart `2.1.43`.
  Значения credentials видимы держателям доступа к Helm release и ConfigMap;
  роль скрывает Helm task через `no_log`. `atomic` и `wait`
  настраиваются одноимёнными переменными с тем же префиксом (defaults `true`).
- `roles/k8s/monitoring/` — общие роли дашбордов Grafana и
  PrometheusRule. Контракты и примеры: [мониторинг](roles/k8s/monitoring/README.md).
- `roles/docker/nfs-server/` provides a shared Docker-based NFS server role.
- `roles/docker/engine/` устанавливает Docker Engine и Docker Compose и
  управляет доступом к группе `docker`.
- `roles/k8s/postgresql/` deploys PostgreSQL to Kubernetes via the Bitnami
  Helm chart (fixed chart and image versions, optional metrics sidecar with
  ServiceMonitor, optional `postgresqlExtendedConf` tuning and extensions).
- `roles/k8s/postgresql_init_db/` creates a PostgreSQL login-role and database
  through a short-lived in-cluster Job using a pinned official PostgreSQL client
  image; it references pre-provisioned Kubernetes Secrets and never manages them.
- `roles/k8s/vault-secrets-operator/` deploys the official HashiCorp VSO Helm
  chart with pinned chart and image versions; per-consumer Vault auth and sync
  resources remain owned by the consumer/infrastructure playbook.
- `roles/k8s/postgresql-backup-monitoring/` provides shared Kubernetes backup
  monitoring for PostgreSQL.
- `roles/hermes/agent_init/` installs and configures a Hermes Agent user
  service.
- `roles/hermes/agent_env/` manages explicit Hermes environment values in the
  user-owned `.env` file.
- `roles/hermes/agent_mcp/` manages one MCP server entry in the Hermes
  configuration without storing secret values in it.
- `roles/hermes/agent_todoist_mcp/` installs the local Todoist MCP server and
  connects it to Hermes using an API key stored in the user environment.
- `roles/hermes/agent_memory/` manages the built-in Hermes memory and user
  profile character limits without modifying stored memory content.
- `roles/hermes/agent_tavily/` configures the Tavily environment token through
  `roles/hermes/agent_env/` and selects the web backend for Hermes.
- `roles/hermes/agent_tool_loop/` manages the Hermes tool-loop hard-stop
  setting.
- `roles/hermes/git_backup/` configures the Hermes Git backup repository,
  scheduler and `GITHUB_BACKUP_TOKEN` environment value.
- `roles/hermes/git_restore/` restores a Hermes home directory from the Git
  backup repository without overwriting existing data.
- `roles/hermes/kubeconfig/` installs an explicitly selected kubeconfig for an
  existing Hermes user without generating cluster credentials.
- `roles/nodejs/runtime/` installs Node.js and npm from NodeSource on Debian
  and Ubuntu hosts.
- `roles/llm/llama-cpp/` deploys a llama.cpp server with Docker Compose,
  loading a model from a Hugging Face GGUF repository (token optional).
- `roles/llm/vllm/` deploys a vLLM server with Docker Compose, including
  optional Ray multi-node setups and `auto` tensor-parallel GPU detection.
- `roles/llm/stable-diffusion-cpp/` builds a pinned CUDA sd-server and serves
  GGUF diffusion models through a bearer-authenticated Docker Compose API.

## Hermes Kubernetes Credentials

`roles/hermes/kubeconfig/` requires an explicit absolute controller-side
`hermes_kubeconfig_source`. It does not search for credentials or contact the
Kubernetes API. The caller supplies privilege escalation and an existing user.

| Role Input | Default | Purpose |
| --- | --- | --- |
| `hermes_kubeconfig_source` | empty, required | Absolute source filename on controller |
| `hermes_kubeconfig_user` | `hermes` | Destination owner |
| `hermes_kubeconfig_group` | `{{ hermes_kubeconfig_user }}` | Destination group |
| `hermes_kubeconfig_user_home` | `/home/{{ hermes_kubeconfig_user }}` | Absolute managed-user home |

The destination is `{{ hermes_kubeconfig_user_home }}/.kube/config`: normally
`/home/hermes/.kube/config`, owned by `hermes:hermes`, mode `0600`, with directory
mode `0700`. Copying replaces the existing file without merging or creating
backups. Credentials are hidden from logs and diffs. Kubernetes clients use this
HOME-based default unless `KUBECONFIG` or explicit client configuration overrides
it. The role does not change the environment, install kubectl, or restart Hermes.

In the HomeLab consumer, `ansible/playbooks/hermes/kubeconfig.yml` accepts only
an explicit source basename through `hermes_kubeconfig_name` under the project's
`ansible/kubeconfigs/`. Its default is `homelab-llm-access`; its default target is
`hermes-vm.ad`, overridable by `hermes_target`. Inventory `hermes_user`,
`hermes_user_group` and `hermes_user_home` are passed to the corresponding role
inputs. The controller source restriction does not prohibit the explicitly
managed destination `.kube/config` on Hermes.

Operator commands from the parent project's `ansible/` directory, shown only
as documentation and not executed:

```sh
pdm run ansible-playbook playbooks/k8s/llm-access.yml
pdm run ansible-playbook playbooks/hermes/kubeconfig.yml -e '{"hermes_target":"hermes-vm.ad","hermes_kubeconfig_name":"homelab-llm-access"}'
```

Generation and upload are separate. The first playbook uses administrative
`kubeconfigs/homelab`, creates the separate `default/llm-access` ServiceAccount
and writes `kubeconfigs/homelab-llm-access`; existing `homelab-ro` and
`homelab-llm` credentials remain unchanged. Access policy, JSON namespace-list
overrides and token revocation are documented in the parent `ansible/AGENTS.md`
and `docs/adr/adr-28-llm-kubernetes-access.md`. The credential is long-lived:
protect all copies, revoke by deleting its token Secret or ServiceAccount, and
explicitly upload again after generation recreates a revoked token. Workload
writes allow indirect Secret access and potential privilege escalation; this
identity is not a strict security sandbox. No deployment was performed as part
of this documentation change.
