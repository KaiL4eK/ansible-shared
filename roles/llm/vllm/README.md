# vLLM role

This role deploys a vLLM server with Docker Compose.

## Tensor parallelism

`vllm_tensor_parallel_size` defaults to `1`. Set it to an integer to use a
fixed tensor-parallel size, or to `auto` to detect the number of GPUs visible
inside the container at every container start.

The `auto` mode is useful when a VM can be recreated with a different GPU
flavor while retaining its disk. The role uses a startup entrypoint and
`nvidia-smi -L`, so Docker restarts use the currently available GPU count
without requiring Ansible to render the Compose file again.

Example:

```yaml
vllm_tensor_parallel_size: auto
```

When using `auto`, `vllm_gpu_devices` must expose the GPUs that should be used.
The default value `all` passes all available GPUs to the container.

## Prompt tokens details

`vllm_enable_prompt_tokens_details` defaults to `true` and passes
`--enable-prompt-tokens-details` to `vllm serve`. This makes the OpenAI API
report `prompt_tokens_details` (including `cached_tokens`) in the usage stats,
which is useful for prefix-cache hit monitoring. Set it to `false` to disable.

The following optional variables configure long-prefill scheduling and the
Mamba SSM cache: `vllm_watermark`, `vllm_mamba_ssm_cache_dtype`,
`vllm_max_num_partial_prefills`, `vllm_max_long_partial_prefills`, and
`vllm_long_prefill_token_threshold`.

## Post-deploy verification

Set `vllm_verify_enabled: true` to verify the deployed server with real API
requests after it becomes healthy:

- `GET /v1/models` — the expected served model
  (`vllm_served_model_name` or `vllm_model_name`) must be listed.
- `POST /v1/chat/completions` with `vllm_verify_prompt` — non-empty assistant
  content is required; when `vllm_verify_expect_contains` is set, that
  case-insensitive substring must appear in the content.

The Compose healthcheck only proves `/health` responds; these checks prove the
model is actually served and generates text.

Additional variables (full defaults in `defaults/main.yml`):
`vllm_verify_timeout` (per-request timeout in seconds), `vllm_verify_max_tokens`,
`vllm_verify_temperature`, `vllm_verify_prompt`, `vllm_verify_expect_contains`.

Requests are sent from the Ansible controller to
`http://<host default IPv4>:<vllm_port>`, so that address must be reachable
from the controller; enable the check only where the network allows it.
`vllm_api_key` is used automatically and is never logged (`no_log`).
