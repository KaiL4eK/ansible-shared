# SGLang role

This role deploys an SGLang server (`sglang serve`) with Docker Compose,
loading a model directly from a Hugging Face repository.

## Model loading

`sglang_model_name` is required (for example `Qwen/Qwen3.5-35B-A3B-FP8`).
Public repositories work without a token; set `sglang_hf_token` only for
gated or private repositories. The token is rendered into the role-managed
`.env` file (`mode 0600`) and consumed by the container.

## Key variables

- `sglang_model_name` — Hugging Face model repo (required).
- `sglang_served_model_name` — optional public model name, defaults to
  `sglang_model_name`.
- `sglang_hf_token` — optional Hugging Face token, defaults to `""`.
- `sglang_image` / `sglang_version` — container image, defaults to
  `lmsysorg/sglang:latest`.
- `sglang_port` / `sglang_container_port` — host and container ports.
- `sglang_gpu_devices` — `all` or a comma-separated list of GPU indices.
- `sglang_tp_size` — tensor parallelism size.
- `sglang_context_length` — optional model context length override.
- `sglang_mem_fraction_static` — optional static memory fraction.
- `sglang_tool_call_parser` / `sglang_reasoning_parser` — OpenAI-compatible
  tool call and reasoning parsers.
- `sglang_trust_remote_code` — pass `--trust-remote-code` when `true`.
- `sglang_pull_enabled` — set to `false` when a locally built image is used.
- `sglang_extra_args` — raw extra `sglang serve` CLI options.
- `sglang_extra_env` — extra environment variables for the container.

Full defaults: see `defaults/main.yml`.

## Example

```yaml
- hosts: my-gpu-host
  roles:
    - llm/sglang
  vars:
    sglang_version: v0.5.10-cu130
    sglang_model_name: Qwen/Qwen3.5-35B-A3B-FP8
    sglang_mem_fraction_static: "0.85"
    sglang_tool_call_parser: qwen3_coder
    sglang_reasoning_parser: qwen3
    # sglang_hf_token: "{{ my_hf_token }}"  # only for gated/private repos
```
