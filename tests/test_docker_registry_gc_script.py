import os
import subprocess
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "roles/k8s/docker-registry-gc/files/registry_gc.sh"


def run_gc_script(tmp_path, gc_exit_code):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    kubectl_log = tmp_path / "kubectl.log"
    fake_kubectl = fake_bin / "kubectl"
    fake_kubectl.write_text(
        "#!/bin/bash\n"
        "printf '%s\\n' \"$*\" >> \"$KUBECTL_LOG\"\n"
        "if [[ \"$*\" == *jsonpath=* ]]; then exit 0; fi\n"
        "if [[ \"$*\" == *' exec '* ]]; then exit \"$GC_EXIT_CODE\"; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_kubectl.chmod(0o755)

    environment = os.environ.copy()
    environment.update(
        {
            "PATH": f"{fake_bin}:{environment['PATH']}",
            "KUBECTL_LOG": str(kubectl_log),
            "GC_EXIT_CODE": str(gc_exit_code),
            "REGISTRY_NAMESPACE": "registry",
            "REGISTRY_DEPLOYMENT": "docker-registry",
            "REGISTRY_CONTAINER": "docker-registry",
            "REGISTRY_BINARY": "/bin/registry",
            "REGISTRY_CONFIG_PATH": "/etc/distribution/config.yml",
            "CLEANUP_JOB_SELECTOR": "app=docker-registry-cleanup",
            "CLEANUP_WAIT_TIMEOUT_SECONDS": "1",
            "ROLLOUT_TIMEOUT": "10m",
            "DELETE_UNTAGGED": "true",
        }
    )
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    return result, kubectl_log.read_text(encoding="utf-8").splitlines()


def test_gc_script_restores_writes_after_success(tmp_path):
    result, commands = run_gc_script(tmp_path, gc_exit_code=0)

    assert result.returncode == 0, result.stderr
    enable_index = next(
        index for index, command in enumerate(commands)
        if 'REGISTRY_STORAGE_MAINTENANCE_READONLY={"enabled":true}' in command
    )
    gc_index = next(index for index, command in enumerate(commands) if " exec " in command)
    restore_index = next(
        index for index, command in enumerate(commands)
        if "REGISTRY_STORAGE_MAINTENANCE_READONLY-" in command
    )
    assert enable_index < gc_index < restore_index
    assert "rollout status deployment/docker-registry" in commands[-1]


def test_gc_script_restores_writes_after_gc_failure(tmp_path):
    result, commands = run_gc_script(tmp_path, gc_exit_code=23)

    assert result.returncode == 23
    assert any(
        "REGISTRY_STORAGE_MAINTENANCE_READONLY-" in command
        for command in commands
    )
    assert "rollout status deployment/docker-registry" in commands[-1]
