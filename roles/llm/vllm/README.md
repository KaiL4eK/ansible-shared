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
