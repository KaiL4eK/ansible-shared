# Hermes WebUI role

Checks out the pinned upstream Hermes WebUI source and runs it as a systemd
service beside the existing Hermes Agent. Its launcher and WebUI requirements
use a dedicated Python 3.12 virtual environment; the pinned upstream bootstrap
selects the Hermes Agent interpreter for the long-running server. The service
runs as the Hermes user on the VM, using the same HOME, `.hermes`, shared skills,
workspace, configuration, credentials and host tools as the Agent.

The role does not install Docker Engine, configure Kubernetes publication, or
load Vault. A consumer explicitly passes deployment paths, HTTPS origin and
password.

## Inputs

| Variable | Default | Purpose |
| --- | --- | --- |
| `hermes_webui_user` / `hermes_webui_group` | `hermes` / same user | Bind-mount owner and runtime UID/GID |
| `hermes_webui_user_home` | `/home/<user>` | Host user home |
| `hermes_webui_home` | `<user-home>/.hermes` | Existing Hermes home mounted in container |
| `hermes_webui_agent_install_directory` | `<hermes-home>/hermes-agent` | Existing Agent source; must contain `pyproject.toml` |
| `hermes_webui_workspace_directory` | `<user-home>/workspace` | Host workspace mounted at `/workspace` |
| `hermes_webui_repository_url` | upstream repository | WebUI Git repository |
| `hermes_webui_repository_revision` | pinned 40-character commit | WebUI source revision and image tag |
| `hermes_webui_install_directory` | `<user-home>/hermes-webui` | Build context checkout path |
| `hermes_webui_venv_directory` | `<install-dir>/.venv` | Isolated WebUI Python dependencies |
| `hermes_webui_python_version` | `3.12` | Python runtime for the WebUI environment |
| `hermes_webui_environment_file` | `/etc/hermes-webui.env` | Root-owned protected runtime environment file |
| `hermes_webui_systemd_unit` | `/etc/systemd/system/hermes-webui.service` | Service unit path |
| `hermes_webui_service_name` | `hermes-webui` | systemd service name |
| `hermes_webui_port` | `8787` | Guest listen port |
| `hermes_webui_password` | empty (required) | Built-in login password |
| `hermes_webui_password_min_length` | `16` | Minimum password length |
| `hermes_webui_allowed_origin` | `https://localhost` | Trusted browser origin |
| `hermes_webui_state_directory` | `<hermes-home>/webui` | Persistent session and WebUI state |
| `hermes_webui_health_retries` / `hermes_webui_health_delay` | `30` / `10` seconds | Bounded health polling (5 minutes maximum) |
| `hermes_webui_health_timeout` | `5` seconds | Per-request health-check timeout |

The role creates a dedicated venv and installs `requirements.txt`, then starts
the upstream `bootstrap.py --foreground --skip-agent-install` under systemd.
The password is stored in a root-owned, Hermes-group-readable mode-0640
EnvironmentFile; template output and diffs are hidden. Deployment stops/removes
the former `hermes-webui` Docker container after preparing the service, avoiding
a port conflict. Docker Engine itself is not removed because it may serve other
workloads. The health check polls for at most five minutes with a short request
timeout and reports safe status if startup does not finish.

Run HomeLab lint and syntax checks from `ansible/`; the role is resolved through
that consumer's `roles_path`.
