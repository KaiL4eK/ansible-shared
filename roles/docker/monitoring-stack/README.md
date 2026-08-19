# docker/monitoring-stack

Роль разворачивает Prometheus, Grafana, Loki и Jaeger одним Docker Compose-проектом.
Каталог проекта по умолчанию: `/home/{{ ansible_user }}/ansible/monitoring`.
Данные сервисов хранятся в именованных Docker volumes, а конфигурации — в
`{{ monitoring_stack_dir }}/config`.
Для Loki и Jaeger Compose запускает одноразовые init-контейнеры, которые
выставляют UID/GID `10001:10001` для storage volumes и завершаются с кодом 0.

На удаленном хосте должны быть установлены Docker Engine, Compose v2 и Python с
доступом к Docker API. Роль сама Docker не устанавливает.

Сервисы управляются флагами `monitoring_stack_enable_prometheus`,
`monitoring_stack_enable_grafana`, `monitoring_stack_enable_loki` и
`monitoring_stack_enable_jaeger`. При отключении сервиса он исключается из Compose,
а соответствующий datasource — из Grafana provisioning.

Образы, порты, retention и scrape-конфигурация вынесены в `defaults/main.yml`.
Именованные volumes создаются самим Docker Compose при запуске включенных сервисов.
Пароль Grafana следует переопределить через inventory или Ansible Vault.

Проверенные на 17.08.2026 версии образов: Prometheus `3.13.2`, Grafana `13.1.3`,
Loki `3.7.6`, Jaeger `2.20.0`. Все сервисы имеют healthcheck; Grafana запускается
только после перехода включенных Prometheus, Loki и Jaeger в состояние `healthy`.

Healthcheck самого Loki использует встроенную проверку конфигурации: в официальном
образе Loki отсутствуют shell-утилиты вроде `wget`.

Внешних role-зависимостей нет. Используется коллекция `community.docker`.

Лицензия: MIT.
