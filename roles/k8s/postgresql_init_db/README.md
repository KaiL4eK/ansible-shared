# PostgreSQL init database through Kubernetes Job

Создаёт/обновляет login-role и database идемпотентной SQL-командой из
короткоживущего Kubernetes Job. PostgreSQL server не устанавливается: Job
подключается к заданному Service/DNS имени. Пин образа по умолчанию — официальный
`postgres:17.6-bookworm`.

Все параметры объявлены в `defaults/main.yml`; namespace и два входных Kubernetes
Secret должны существовать заранее. Роль не создаёт, не изменяет и не удаляет
Secret или ConfigMap: единственный создаваемый ресурс — Job. Пароли Job получает
через `secretKeyRef`; значения паролей не попадают в Ansible args, Job spec или
логи. Роль ждёт `Complete` или `Failed`, завершает play с ошибкой при неуспехе.
Job автоматически очищается TTL-контроллером через 10 минут, Pod не получает
ServiceAccount token.

Для выполнения нужны права только на Job и чтение его статуса в целевом
namespace. Secret’ы должны быть заранее синхронизированы VSO и защищены
namespace-scoped RBAC и encryption at rest. DB-init следует запускать в
инфраструктурном namespace, недоступном приложенческому CI.
