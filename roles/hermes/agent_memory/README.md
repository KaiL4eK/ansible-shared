# Hermes Agent memory role

This role configures the built-in Hermes Agent `MEMORY.md` and `USER.md`
character limits without modifying either memory file.

## Main variables

```yaml
hermes_agent_memory_user: hermes
hermes_agent_memory_user_home: /home/hermes
hermes_agent_memory_home: /home/hermes/.hermes
hermes_agent_memory_binary_path: /home/hermes/.local/bin/hermes
hermes_agent_memory_char_limit: 2200
hermes_agent_memory_user_char_limit: 1375
```

The role reads the active settings through `hermes config get`, changes only
values that differ, verifies both limits, and restarts the Hermes gateway when
configuration changed. Ansible check mode validates inputs and the binary path
without changing the Hermes configuration.

## Usage

```yaml
roles:
  - role: hermes/agent_memory
    vars:
      hermes_agent_memory_char_limit: 6000
      hermes_agent_memory_user_char_limit: 3000
```
