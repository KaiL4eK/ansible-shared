# ansible-shared

Reusable Ansible roles for shared automation.

## Purpose

`ansible-shared` is a small library of reusable Ansible roles that can be consumed from different playbook collections.

This repository should contain generic role logic, not environment-specific inventory, vault content, or orchestration glue.

## Structure

- `roles/` contains shared roles grouped by domain using `roles/<domain>/<role-name>`.
- `.agents/skills/` contains local skills for implementing and reviewing shared roles.
- `requirements.yml` defines external role and collection dependencies for this repository.
- `AGENTS.md` contains local development rules.
- `LICENSE` defines reuse terms for this repository.

## Preparation

Before working with this repository, install Ansible dependencies:

`ansible-galaxy collection install -r requirements.yml`

## Local Skills

- `.agents/skills/ansible-role/SKILL.md` describes how to create and refine roles in this repository.

## Current Content

- `roles/docker/nfs-server/` provides a shared Docker-based NFS server role.
- `roles/k8s/postgresql-backup-monitoring/` provides shared Kubernetes backup
  monitoring for PostgreSQL.
