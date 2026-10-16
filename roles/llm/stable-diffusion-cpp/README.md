# llm/stable-diffusion-cpp

Build a pinned CUDA `sd-server` and serve a GGUF diffusion model with Docker
Compose. With authentication enabled, requests go through a bearer-authenticated
nginx proxy; with authentication disabled, `sd-server` is published directly.
Inference is serialized by sd-server.

## Requirements

- Docker Engine, Compose v2, Buildx and NVIDIA Container Toolkit on the target.
- Git on the target; public Hugging Face downloads and CUDA container access.
- `community.docker` (declared in the shared repository requirements).
- Adequate RAM, GPU memory and disk space for the build, weights and buffers.

## Inputs

Required inputs default to `null`, except `sdcpp_models` (empty list):

- `sdcpp_remote_dir`: absolute deployment directory.
- `sdcpp_revision`: full stable-diffusion.cpp commit SHA.
- `sdcpp_cuda_architectures`: CUDA CMake target, e.g. `121` for GB10.
- `sdcpp_api_key`: bearer key supplied from the consuming environment when
  `sdcpp_auth_enabled` is true; accepts letters, digits, `_` and `-`. Never put
  a real key in version control.
- `sdcpp_models`: entries with `repo`, full `revision`, `file` and `sha256`.
  Files are downloaded into `models/` using their basenames, which must be unique.
- `sdcpp_diffusion_model_file`, `sdcpp_text_encoder_file`, `sdcpp_vae_file`:
  downloaded component basenames.

Optional inputs:

| Variable | Default | Purpose |
| --- | --- | --- |
| `sdcpp_source_repo` | upstream leejet GitHub repository | Source repository |
| `sdcpp_required_architecture` | `null` | Optional Ansible host architecture check |
| `sdcpp_cuda_version` | `13.0.2` | CUDA build/runtime image version |
| `sdcpp_build_parallelism` | `2` | Compiler concurrency |
| `sdcpp_image` | `null` | Explicit image name; normally source/build-derived |
| `sdcpp_api_image` | `nginx:1.28-alpine` | API proxy image when authentication is enabled |
| `sdcpp_port` | `8080` | Published API or proxy port |
| `sdcpp_auth_enabled` | `true` | Require a bearer token on API requests |
| `sdcpp_extra_args` | `[]` | Additional sd-server arguments as strings |
| `sdcpp_compose_wait_timeout` | `1800` | Startup wait in seconds |

Model selection, generation defaults, license compliance and replacement of any
existing service belong in the consuming playbook. Image editing requires
matching vision weights and `--llm_vision` in `sdcpp_extra_args`.

## Usage

Define all required inputs in inventory or play vars, including an API key
reference to your secret store, then invoke:

```yaml
- name: Deploy image generation
  hosts: image_servers
  roles:
    - llm/stable-diffusion-cpp
```

For a service replacement, use the split entrypoints:

```yaml
tasks:
  - name: Prepare replacement without starting it
    ansible.builtin.include_role:
      name: llm/stable-diffusion-cpp
      tasks_from: prepare

  # Stop the old service here using playbook-owned paths and variables.

  - name: Start prepared service
    ansible.builtin.include_role:
      name: llm/stable-diffusion-cpp
      tasks_from: start
```

Preparation builds the image, verifies model downloads, writes configuration and
pulls nginx when authentication is enabled, without starting the service. Start
uses the prepared files and waits for healthchecks. The entrypoints must run in
order in the same play.

Keep `sdcpp_auth_enabled` enabled for any network-exposed deployment. Disabling
it is intended only for temporary isolated testing.

The source/Dockerfile-derived image name avoids rebuilding unchanged inputs.
When authentication is enabled, proxy configuration changes update a Compose
label and recreate the proxy, so a separate restart handler is not needed.
Explicit image names rebuild when the source checkout or Dockerfile changes.

The role does not stop other services, delete weights, configure TLS or validate
inference performance. `/v1/images/generations` provides the OpenAI-compatible
generation API. Test generation and memory use before announcing availability.
