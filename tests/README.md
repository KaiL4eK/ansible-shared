# Проверка PostgreSQL bootstrap

Из корня инфраструктурного репозитория:

```sh
pdm run python ansible/ansible-shared/tests/check_postgresql_bootstrap.py \
  --work-dir .tmp/postgresql-bootstrap --ansible-directory ansible
```

Нужны Docker, локальный образ `postgres:17-alpine`, Ansible,
community.postgresql, PyYAML и psycopg2. Другой тестовый образ выбирается через
`--image`. Скрипт поднимает собственный временный контейнер с динамическим
localhost-портом и удаляет его в `finally`. Рабочие БД, кластер и vault не
используются; Ansible запускается из указанной директории с изолированным
config. Временные playbook/config остаются только в указанном `--work-dir`.

Проверяются прямой вызов роли и реальный shell/SQL из Job: создание, повтор,
неизменность хеша пароля, ошибка для неверного пароля с существующей и
отсутствующей БД, конфликт владельца и отказ при `trust`. Прямая роль также
проверяется без admin credentials и в check mode для отсутствующего пользователя.
