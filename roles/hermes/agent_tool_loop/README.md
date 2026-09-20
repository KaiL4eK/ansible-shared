# Hermes Agent tool-loop role

This role configures the Hermes tool-loop hard-stop setting independently from
Hermes installation and initialization.

The role reads the current value, changes it only when necessary, verifies the
result, and restarts the Hermes gateway only after a change.

## Main variables

```yaml
hermes_agent_tool_loop_user: hermes
hermes_agent_tool_loop_user_home: /home/hermes
hermes_agent_tool_loop_home: /home/hermes/.hermes
hermes_agent_tool_loop_binary_path: /home/hermes/.local/bin/hermes
hermes_agent_tool_loop_runtime_environment:
  HOME: /home/hermes
  HERMES_HOME: /home/hermes/.hermes
hermes_agent_tool_loop_hard_stop_enabled: true
```

The role expects the Hermes binary to be installed already.
