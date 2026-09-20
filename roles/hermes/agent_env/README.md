# Hermes Agent environment role

This role writes explicitly supplied Hermes environment values to the user-owned
`.env` file with restrictive permissions. Values are hidden from Ansible output
and the gateway is restarted only when a value changes.

## Main variables

```yaml
hermes_agent_env_user: hermes
hermes_agent_env_group: hermes
hermes_agent_env_user_home: /home/hermes
hermes_agent_env_home: /home/hermes/.hermes
hermes_agent_env_file: /home/hermes/.hermes/.env
hermes_agent_env_binary_path: /home/hermes/.local/bin/hermes
hermes_agent_env_values:
  EXAMPLE_TOKEN: value
```
