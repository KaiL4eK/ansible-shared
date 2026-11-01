# Hermes WebUI role

Builds the pinned upstream Hermes WebUI Docker image on the managed host and
runs it beside an existing Hermes Agent. The container bind-mounts the existing
`.hermes` directory and workspace, so configuration, credentials, Agent source,
and WebUI state remain on the Hermes VM. The container creates its own Python
environment; it does not use or alter the host Agent virtual environment.

The role does not install Docker Engine, configure Kubernetes publication, or
load Vault. A consumer must install Docker Engine and explicitly pass deployment
paths, HTTPS origin and password.

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
| `hermes_webui_image_name` | `localhost/hermes-webui:<revision>` | Locally built image |
| `hermes_webui_container_name` | `hermes-webui` | Docker container name |
| `hermes_webui_port` | `8787` | Guest listen port |
| `hermes_webui_password` | empty (required) | Built-in login password |
| `hermes_webui_password_min_length` | `16` | Minimum password length |
| `hermes_webui_allowed_origin` | `https://localhost` | Trusted browser origin |
| `hermes_webui_state_directory` | `<hermes-home>/webui` | Persistent session and WebUI state |
| `hermes_webui_health_retries` / `hermes_webui_health_delay` | `30` / `10` seconds | Bounded health polling (5 minutes maximum) |
| `hermes_webui_health_timeout` | `5` seconds | Per-request health-check timeout |

The role installs the Docker SDK, checks out the pinned source, builds the image
and starts it with `unless-stopped`. It manages only the container deployment;
it does not manage prior WebUI installations. It passes the managed user's
numeric UID/GID so upstream container initialization preserves host file
ownership. The container task and password validation use `no_log`/`diff: false`.
On first startup, the upstream entrypoint installs Agent dependencies into the
container's separate Python environment. The health check polls for at most five
minutes with a short request timeout and reports safe container state if startup
does not finish.

Run HomeLab lint and syntax checks from `ansible/`; the role is resolved through
that consumer's `roles_path`.
