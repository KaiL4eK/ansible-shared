# docker/engine

Устанавливает Docker Engine, Docker Compose plugin и Python SDK для Docker на
Debian/Ubuntu-хостах.

Роль также добавляет пользователя `docker_engine_user` в группу
`docker_engine_docker_group`. По умолчанию используется пользователь Ansible.
После изменения группы выполняется `meta: reset_connection`, чтобы последующие
задачи работали с обновлёнными группами без ручного переподключения.

Основные переменные находятся в `defaults/main.yml`. Для нестандартного
пользователя можно передать:

```yaml
docker_engine_user: devadmin
```
