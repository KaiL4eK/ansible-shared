# whisper.cpp role

This role deploys a whisper.cpp speech-to-text server (`whisper-server`) with
Docker Compose. It clones the whisper.cpp repository on the target host,
builds the CUDA image locally, downloads a pinned GGML model from
Hugging Face and starts the server with its OpenAI-compatible HTTP API
(`/v1/audio/transcriptions` when configured via
`whisper_cpp_additional_options`).

## Key variables

- `whisper_cpp_repo` / `whisper_cpp_repo_ref` — source repository and ref to
  build the image from (for example `v1.8.1`).
- `whisper_cpp_image` / `whisper_cpp_version` — local image name and tag; the
  default tag follows the ref with a `-cuda` suffix.
- `whisper_cpp_build_enabled` — clone and build the CUDA image on the target
  host (default `true`); set `false` only to reuse an already built image.
- `whisper_cpp_build_platform` — build platform; defaults to `linux/arm64` on
  aarch64 hosts (NVIDIA DGX Spark) and `linux/amd64` otherwise.
- `whisper_cpp_pull_enabled` — run `docker compose pull` before start
  (default `false`, the image is local).
- `whisper_cpp_port` — HTTP server port (host and container, default `8081`).
- `whisper_cpp_model_filename` / `whisper_cpp_model_url` — GGML model file,
  downloaded into the role-managed models directory (default
  `ggml-large-v3-turbo.bin` from `ggerganov/whisper.cpp`).
- `whisper_cpp_use_gpu` — GPU passthrough via Docker device reservations;
  when `false` the server starts with `--no-gpu`.
- `whisper_cpp_strip_cuda_compat_ld_path` — drop `*/compat*` paths from
  `LD_LIBRARY_PATH` before starting `whisper-server` (default `true`); avoids
  CUDA driver/runtime conflicts on hosts with NVIDIA container tooling.
- `whisper_cpp_enable_flash_attn` — pass `--flash-attn` (default `true`).
- `whisper_cpp_threads` / `whisper_cpp_processors` — CPU decode threads
  (default: all vCPUs) and processors.
- `whisper_cpp_additional_options` — raw extra `whisper-server` CLI options,
  for example `--inference-path /v1/audio/transcriptions`.
- `whisper_cpp_remote_dir` — per-host working directory (defaults to
  `/home/<user>/ansible/whisper-cpp`).

Full defaults: see `defaults/main.yml`.

## Example

```yaml
- hosts: my-gpu-host
  roles:
    - llm/whisper-cpp
  vars:
    whisper_cpp_repo_ref: v1.8.1
    whisper_cpp_build_platform: linux/arm64
    whisper_cpp_port: 8081
    whisper_cpp_model_filename: ggml-large-v3-turbo.bin
    whisper_cpp_model_url: "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin"
    whisper_cpp_additional_options: "--inference-path /v1/audio/transcriptions"
```

## Notes

- The service is deployed without authentication on its port; access control
  is expected from the upstream proxy (for example Bifrost / LLM Proxy) in
  front of it.
- The service runs one transcription request at a time — no concurrency.
