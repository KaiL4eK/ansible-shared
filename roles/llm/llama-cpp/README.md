# llama.cpp role

This role deploys a llama.cpp server (`llama-server`) with Docker Compose,
loading a model directly from a Hugging Face GGUF repository (`-hf` mode).
It either pulls a prebuilt image or builds llama-server on the target host
for GPUs that prebuilt images do not cover.

## Model loading

`llama_cpp_hf_model_repo` is required (for example
`unsloth/Qwen3.8-Flash-Next-GGUF:UD-Q4_K_XL`). Public repositories work
without a token; set `llama_cpp_hf_token` only for gated or private
repositories. The token is rendered into the role-managed `.env` file
(`mode 0600`) and consumed by the container.

## Key variables

- `llama_cpp_hf_model_repo` — Hugging Face GGUF repo (required).
- `llama_cpp_hf_token` — optional Hugging Face token, defaults to `""`.
- `llama_cpp_api_key` — optional Bearer API key; rendered into the `.env`
  (mode 0600) and consumed via `LLAMA_API_KEY`. `/health` stays public, so
  the Compose healthcheck keeps working. Defaults to `""` (no auth).
- `llama_cpp_hf_model_file` — optional exact model filename from the repo.
- `llama_cpp_hf_mmproj_file` — optional mmproj file for multimodal models.
- `llama_cpp_draft_model` — optional draft model path for speculative decoding.
- `llama_cpp_use_gpu` / `llama_cpp_gpu_layers` — GPU passthrough and layer offload.
- `llama_cpp_ctx_size`, `llama_cpp_threads`, `llama_cpp_batch_size`,
  `llama_cpp_ubatch_size`, `llama_cpp_n_predict` — server sizing options.
- `llama_cpp_additional_options` — raw extra `llama-server` CLI options.
- `llama_cpp_extra_env` — extra environment variables for the container.
- `llama_cpp_pull_enabled` — set to `false` when a locally built image is used
  without the build mode below.
- `llama_cpp_healthcheck_start_period` — Compose healthcheck `start_period`,
  useful when the first start downloads the model weights (example: `1h`).

Full defaults: see `defaults/main.yml`.

## Local image build

Set `llama_cpp_build_enabled: true` to clone llama.cpp on the target host,
compile `llama-server` inside a CUDA build image and run it from the
resulting local image. This is required for GPUs that upstream prebuilt
images do not support — for example NVIDIA DGX Spark (GB10, `sm_121a`),
which needs CUDA 13 and `llama_cpp_cuda_architectures: 121a`.

Build-specific variables:

- `llama_cpp_source_repo` — llama.cpp Git repository.
- `llama_cpp_revision` — full 40-hex commit SHA to build (required).
- `llama_cpp_required_architecture` — optional host architecture check,
  for example `aarch64` (build happens on the target host).
- `llama_cpp_cuda_version` — `nvidia/cuda` build/runtime image version.
- `llama_cpp_cuda_architectures` — CMake `CMAKE_CUDA_ARCHITECTURES` target.
- `llama_cpp_build_parallelism` — compiler concurrency (GB10 has limited
  memory; keep it low).
- `llama_cpp_build_config` — extra CMake defines, for example
  `{GGML_CUDA_FA_ALL_QUANTS: "ON"}` to support flash attention with a
  quantized KV cache (`-ctk q8_0`).
- `llama_cpp_build_image` — optional explicit image name; by default the
  image is tagged from the source revision and Dockerfile checksum, so
  unchanged inputs are not rebuilt.

With the build enabled the image is never pulled; the Compose project starts
from the local image only.

## Post-deploy verification

Set `llama_cpp_verify_enabled: true` to verify the deployed server with real
API requests after it becomes healthy:

- `GET /v1/models` — at least one model must be served; its id is resolved
  from the first entry, so it works with and without `--alias`.
- `POST /v1/chat/completions` with `llama_cpp_verify_prompt` — non-empty
  assistant content is required; when `llama_cpp_verify_expect_contains` is
  set, that case-insensitive substring must appear in the content.

The Compose healthcheck only proves `/health` responds; these checks prove the
model is actually loaded and generates text.

Additional variables (full defaults in `defaults/main.yml`):
`llama_cpp_verify_timeout` (per-request timeout in seconds),
`llama_cpp_verify_max_tokens`, `llama_cpp_verify_temperature`,
`llama_cpp_verify_prompt`, `llama_cpp_verify_expect_contains`.

Requests are sent from the Ansible controller to
`http://<host default IPv4>:<llama_cpp_port>`, so that address must be
reachable from the controller; enable the check only where the network allows
it. `llama_cpp_api_key` is used automatically and is never logged (`no_log`).

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

Example with a local build for NVIDIA DGX Spark (GB10):

```yaml
- hosts: waml-dgx-spark-2
  roles:
    - llm/llama-cpp
  vars:
    llama_cpp_build_enabled: true
    llama_cpp_revision: 620d2225cc436ab0b001e3200e590e3b286ef9ab  # v0.7.0
    llama_cpp_required_architecture: aarch64
    llama_cpp_cuda_architectures: "121a"
    llama_cpp_build_config:
      GGML_CUDA_FA_ALL_QUANTS: "ON"
    llama_cpp_hf_model_repo: deadbydawn101/RavenX-CyberAgent-Qwen3.6-35B-A3B-Opus-4.7-OpenMythos-Pentester-BugHunter-RATH-GGUF
    llama_cpp_hf_model_file: RavenX-CyberAgent-35B-v5.1-Q4_K_M.gguf
    llama_cpp_ctx_size: 262144
    llama_cpp_healthcheck_start_period: 1h
```
