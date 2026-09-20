# Hermes Agent initialization role

This role installs and configures Hermes Agent for a dedicated Linux user and
runs its messaging gateway as a Hermes-managed systemd user service.

The role intentionally does not run `hermes setup`, `hermes gateway setup`, or
write `onboarding.seen`. It also does not template the gateway unit. Instead,
Hermes creates and owns `~/.config/systemd/user/hermes-gateway.service`; the
role enables user lingering and uses `hermes gateway restart` for configuration
changes. Hermes receives the first Telegram message only after the technical
provisioning is complete, so its normal onboarding flow remains user-driven.

## Main variables

```yaml
hermes_user: hermes
hermes_model_provider: custom
hermes_model: model-name
hermes_model_base_url: https://llm-proxy.example/v1
hermes_reasoning_effort: medium
hermes_model_api_key: ""
hermes_telegram_bot_token: "{{ vault_hermes_telegram_bot_token }}"
hermes_telegram_user_ids:
  - "123456789"
  - "987654321"
hermes_telegram_chat_id: "123456789"
hermes_telegram_require_mention: false
```

Model and Telegram settings are applied with `hermes config set`. The model API
key is stored as `model.api_key`; Hermes stores the Telegram bot token through
its normal secret configuration path. Telegram allowlists are stored in
`config.yaml`.
When enabled, Hermes responds in Telegram groups only when the bot is
mentioned.

The Telegram chat ID is written both to the response allowlist and to the group
chat authorization allowlist. The latter is harmless for a private chat and
permits the configured group to receive messages when the ID is a Telegram
group ID.

## Runtime state

Non-secret settings are changed with `hermes config set`, which preserves the
existing Hermes configuration and runtime keys. The role never manages memory,
sessions, `state.db`, or `onboarding.seen`.

User lingering keeps the Hermes service running after logout and across
reboots. The role manages only the Hermes user systemd service and does not
modify any existing system-scoped gateway unit.

## Usage

```yaml
roles:
  - hermes/agent_init
```

Validate from `ansible-shared/` with `yamllint roles/hermes/agent_init` and
`pdm run ansible-lint roles/hermes/agent_init`.
