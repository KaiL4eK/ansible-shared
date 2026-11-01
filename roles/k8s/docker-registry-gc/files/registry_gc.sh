#!/bin/bash
set -Eeuo pipefail

: "${REGISTRY_NAMESPACE:?REGISTRY_NAMESPACE is required}"
: "${REGISTRY_DEPLOYMENT:?REGISTRY_DEPLOYMENT is required}"
: "${REGISTRY_CONTAINER:?REGISTRY_CONTAINER is required}"
: "${REGISTRY_BINARY:?REGISTRY_BINARY is required}"
: "${REGISTRY_CONFIG_PATH:?REGISTRY_CONFIG_PATH is required}"
: "${CLEANUP_JOB_SELECTOR:?CLEANUP_JOB_SELECTOR is required}"
: "${CLEANUP_WAIT_TIMEOUT_SECONDS:?CLEANUP_WAIT_TIMEOUT_SECONDS is required}"
: "${ROLLOUT_TIMEOUT:?ROLLOUT_TIMEOUT is required}"
: "${DELETE_UNTAGGED:?DELETE_UNTAGGED is required}"

readonly_env_name=REGISTRY_STORAGE_MAINTENANCE_READONLY
readonly_change_started=false

log() {
  printf '[registry-gc] %s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

registry_kubectl() {
  kubectl --namespace "$REGISTRY_NAMESPACE" "$@"
}

restore_registry_writes() {
  local exit_code=$?
  trap - EXIT INT TERM
  set +e

  if [[ "$readonly_change_started" == true ]]; then
    log "Restoring registry write access"
    if ! registry_kubectl set env "deployment/$REGISTRY_DEPLOYMENT" "${readonly_env_name}-"; then
      log "ERROR: unable to remove the temporary registry read-only setting"
      exit_code=1
    elif ! registry_kubectl rollout status "deployment/$REGISTRY_DEPLOYMENT" \
      --timeout="$ROLLOUT_TIMEOUT"; then
      log "ERROR: registry rollout did not complete after restoring write access"
      exit_code=1
    else
      log "Registry is ready with its normal write configuration"
    fi
  fi

  exit "$exit_code"
}

trap restore_registry_writes EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

log "Waiting for registry tag cleanup jobs to finish"
start_seconds=$SECONDS
while true; do
  active_job_counts="$(registry_kubectl get jobs \
    --selector="$CLEANUP_JOB_SELECTOR" \
    -o 'jsonpath={range .items[*]}{.status.active}{" "}{end}')"
  if [[ ! "$active_job_counts" =~ (^|[[:space:]])[1-9][0-9]*([[:space:]]|$) ]]; then
    break
  fi
  if (( SECONDS - start_seconds >= CLEANUP_WAIT_TIMEOUT_SECONDS )); then
    fail "tag cleanup jobs did not finish within ${CLEANUP_WAIT_TIMEOUT_SECONDS}s"
  fi
  sleep 30
done

existing_readonly_state="$(registry_kubectl get deployment "$REGISTRY_DEPLOYMENT" \
  -o "jsonpath={range .spec.template.spec.containers[?(@.name==\"${REGISTRY_CONTAINER}\")].env[?(@.name==\"${readonly_env_name}\")]}{.name}{\"|\"}{.value}{\"|\"}{.valueFrom.secretKeyRef.name}{\"|\"}{.valueFrom.configMapKeyRef.name}{\"|\"}{.valueFrom.fieldRef.fieldPath}{\"|\"}{.valueFrom.resourceFieldRef.resource}{end}")"
if [[ -n "$existing_readonly_state" ]]; then
  IFS='|' read -r existing_name existing_value secret_ref configmap_ref field_ref resource_ref \
    <<< "$existing_readonly_state"
  [[ "$existing_name" == "$readonly_env_name" ]] || fail "unexpected read-only environment state"
  [[ -z "$secret_ref$configmap_ref$field_ref$resource_ref" ]] || \
    fail "read-only environment is already sourced from a Kubernetes reference"
  [[ -z "$existing_value" || "$existing_value" == '{"enabled":true}' || \
    "$existing_value" == '{"enabled":false}' ]] || \
    fail "read-only environment must be unset or a JSON enabled boolean"
fi

readonly_change_started=true
log "Enabling registry read-only mode (pulls remain available; writes are blocked)"
registry_kubectl set env "deployment/$REGISTRY_DEPLOYMENT" \
  "${readonly_env_name}={\"enabled\":true}"
registry_kubectl rollout status "deployment/$REGISTRY_DEPLOYMENT" \
  --timeout="$ROLLOUT_TIMEOUT"

log "Running registry garbage collection"
registry_kubectl exec "deployment/$REGISTRY_DEPLOYMENT" \
  --container="$REGISTRY_CONTAINER" -- \
  "$REGISTRY_BINARY" garbage-collect "--delete-untagged=$DELETE_UNTAGGED" \
  "$REGISTRY_CONFIG_PATH"
log "Registry garbage collection completed"
