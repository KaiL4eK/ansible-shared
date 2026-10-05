# llama.cpp role

This role deploys a llama.cpp server (`llama-server`) with Docker Compose,
loading a model directly from a Hugging Face GGUF repository (`-hf` mode).

## Model loading

`llama_cpp_hf_model_repo` is required (for example
`unsloth/Qwen3.8-Flash-Next-GGUF:UD-Q4_K_XL`). Public repositories work
without a token; set `llama_cpp_hf_token` only for gated or private
repositories. The token is rendered into the role-managed `.env` file
(`mode 0600`) and consumed by the container.

## Key variables

- `llama_cpp_hf_model_repo` — Hugging Face GGUF repo (required).
- `llama_cpp_hf_token` — optional Hugging Face token, defaults to `""`.
- `llama_cpp_hf_model_file` — optional exact model filename from the repo.
- `llama_cpp_hf_mmproj_file` — optional mmproj file for multimodal models.
- `llama_cpp_draft_model` — optional draft model path for speculative decoding.
- `llama_cpp_use_gpu` / `llama_cpp_gpu_layers` — GPU passthrough and layer offload.
- `llama_cpp_ctx_size`, `llama_cpp_threads`, `llama_cpp_batch_size`,
  `llama_cpp_ubatch_size`, `llama_cpp_n_predict` — server sizing options.
- `llama_cpp_additional_options` — raw extra `llama-server` CLI options.
- `llama_cpp_extra_env` — extra environment variables for the container.
- `llama_cpp_pull_enabled` — set to `false` when a locally built image is used.
- `llama_cpp_healthcheck_start_period` — extra start period for the Compose
  healthcheck, useful when the first start downloads the model weights.

Full defaults: see `defaults/main.yml`.

## Example

```yaml
- hosts: my-gpu-host
  roles:
    - llm/llama-cpp
  vars:
    llama_cpp_hf_model_repo: unsloth/Qwen3.8-Flash-Next-GGUF:UD-Q4_K_XL
    llama_cpp_use_gpu: true
    llama_cpp_gpu_layers: 999
    llama_cpp_ctx_size: 102400
    # llama_cpp_hf_token: "{{ my_hf_token }}"  # only for gated/private repos
```
