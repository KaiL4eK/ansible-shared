"""Изолированные интеграционные проверки обоих bootstrap-путей (Docker + Ansible)."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid

import yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--ansible-directory", type=Path, required=True)
    parser.add_argument("--image", default="postgres:17-alpine")
    args = parser.parse_args()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    ansible_dir = args.ansible_directory.resolve()
    shared = Path(__file__).resolve().parents[1]
    container = "bootstrap-test-" + uuid.uuid4().hex[:12]

    def run(command, **kwargs):
        return subprocess.run(command, text=True, capture_output=True, check=False, **kwargs)

    def sql(query):
        result = run(["docker", "exec", container, "psql", "-U", "postgres", "-Atc", query])
        assert result.returncode == 0, result.stderr
        return result.stdout.strip()

    config = work / "ansible.cfg"
    config.write_text("[defaults]\nretry_files_enabled = False\nhost_key_checking = False\n")
    env = dict(os.environ, ANSIBLE_CONFIG=str(config))
    # Не наследовать инфраструктурную загрузку vault или пользовательские extra vars.
    env.pop("ANSIBLE_VAULT_PASSWORD_FILE", None)
    env.pop("ANSIBLE_LOG_PATH", None)
    shell = yaml.safe_load(
        (shared / "roles/k8s/postgresql_init_db/tasks/job.yml").read_text()
    )[1]["kubernetes.core.k8s"]["definition"]["spec"]["template"]["spec"]["containers"][0]["args"][0]

    started = run([
        "docker", "run", "--detach", "--rm", "--name", container,
        "-e", "POSTGRES_PASSWORD=test-admin-password", "-p", "127.0.0.1::5432", args.image,
    ])
    assert started.returncode == 0, started.stderr
    try:
        for _ in range(60):
            ready = run(["docker", "exec", container, "pg_isready", "-U", "postgres"])
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            raise AssertionError("Тестовый PostgreSQL не запустился")
        port = json.loads(run(["docker", "inspect", container]).stdout)[0]["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
        configured = run([
            "docker", "exec", container, "sh", "-ec",
            'printf "local all all trust\\nhost all all all scram-sha-256\\n" > "$PGDATA/pg_hba.conf"',
        ])
        assert configured.returncode == 0, configured.stderr
        sql("SELECT pg_reload_conf()")
        time.sleep(1)

        def bootstrap(mode, user, database, password, admin=True, check=False):
            if mode == "job":
                result = run([
                    "docker", "exec", "-i",
                    "-e", "PGHOST=127.0.0.1", "-e", "PGDATABASE=postgres",
                    "-e", "PGUSER=postgres", "-e", "PGPASSWORD=test-admin-password",
                    "-e", f"APP_DB_USER={user}", "-e", f"APP_DB_PASSWORD={password}",
                    "-e", f"APP_DATABASE={database}", container, "/bin/sh", "-ec", shell,
                ])
            else:
                playbook = work / "bootstrap.yml"
                playbook.write_text(yaml.safe_dump([{
                    "name": "Проверка PostgreSQL bootstrap",
                    "hosts": "localhost", "connection": "local", "gather_facts": False,
                    "roles": [{"role": str(shared / "roles/postgresql/init-db"), "vars": {
                        "postgresql_init_db_host": "127.0.0.1",
                        "postgresql_init_db_port": int(port),
                        "postgresql_init_db_admin_user": "postgres" if admin else "",
                        "postgresql_init_db_admin_password": "test-admin-password" if admin else "",
                        "postgresql_init_db_user": user,
                        "postgresql_init_db_user_password": password,
                        "postgresql_init_db_name": database,
                    }}],
                }]))
                command = ["ansible-playbook", str(playbook)]
                if check:
                    command.append("--check")
                result = run(command, cwd=ansible_dir, env=env)
            assert password not in result.stdout + result.stderr, "Пароль попал в лог"
            return result

        for mode in ("direct", "job"):
            user, db = f"{mode}_user", f"{mode}_db"
            if mode == "direct":
                dry = bootstrap(mode, user, db, "original-test-password", check=True)
                assert dry.returncode == 0, dry.stdout + dry.stderr
                assert sql(f"SELECT count(*) FROM pg_roles WHERE rolname = '{user}'") == "0"
            first = bootstrap(mode, user, db, "original-test-password")
            assert first.returncode == 0, first.stdout + first.stderr
            before = sql(f"SELECT rolpassword FROM pg_authid WHERE rolname = '{user}'")
            repeat = bootstrap(mode, user, db, "original-test-password")
            assert repeat.returncode == 0, repeat.stdout + repeat.stderr
            if mode == "direct":
                assert "changed=0" in repeat.stdout, "Повтор должен быть идемпотентным"
            assert sql(f"SELECT rolpassword FROM pg_authid WHERE rolname = '{user}'") == before
            extra = bootstrap(mode, user, f"{mode}_extra_db", "original-test-password")
            assert extra.returncode == 0, extra.stdout + extra.stderr
            assert sql(f"SELECT rolpassword FROM pg_authid WHERE rolname = '{user}'") == before
            wrong = bootstrap(mode, user, f"{mode}_must_not_exist", "wrong-test-password")
            assert wrong.returncode != 0, "Неверный пароль должен приводить к ошибке"
            assert sql(f"SELECT rolpassword FROM pg_authid WHERE rolname = '{user}'") == before
            assert sql(f"SELECT count(*) FROM pg_database WHERE datname = '{mode}_must_not_exist'") == "0"
            wrong_existing = bootstrap(mode, user, db, "wrong-test-password")
            assert wrong_existing.returncode != 0
            sql(f"ALTER DATABASE {db} OWNER TO postgres")
            conflict = bootstrap(mode, user, db, "original-test-password")
            assert conflict.returncode != 0
            assert sql(f"SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '{db}'") == "postgres"
            sql(f"ALTER DATABASE {db} OWNER TO {user}")
            if mode == "direct":
                no_admin = bootstrap(mode, user, db, "original-test-password", admin=False)
                assert no_admin.returncode == 0, no_admin.stdout + no_admin.stderr
                no_admin_wrong = bootstrap(mode, user, db, "wrong-test-password", admin=False)
                assert no_admin_wrong.returncode != 0
                sql(f"ALTER ROLE {user} CREATEDB VALID UNTIL '2099-01-01'")
                no_admin_create = bootstrap(mode, user, "no_admin_db", "original-test-password", admin=False)
                assert no_admin_create.returncode == 0, no_admin_create.stdout + no_admin_create.stderr
                preserved = bootstrap(mode, user, db, "original-test-password")
                assert preserved.returncode == 0, preserved.stdout + preserved.stderr
                assert sql(f"SELECT rolcreatedb AND rolvaliduntil = '2099-01-01'::timestamptz FROM pg_roles WHERE rolname = '{user}'") == "t"
                sql(f"ALTER DATABASE {db} OWNER TO postgres")
                no_admin_conflict = bootstrap(mode, user, db, "original-test-password", admin=False)
                assert no_admin_conflict.returncode != 0
                sql(f"ALTER DATABASE {db} OWNER TO {user}")
            print(f"OK: {mode}: создание, повтор, неверный пароль, конфликт владельца")

        hyphenated = bootstrap("job", "job-hyphen-user", "job-hyphen-db", "hyphen-test-password")
        assert hyphenated.returncode == 0, hyphenated.stdout + hyphenated.stderr
        assert sql("SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = 'job-hyphen-db'") == "job-hyphen-user"
        print("OK: Job поддерживает дефисы в имени пользователя и БД")

        # Trust не должен давать ложное подтверждение совпадения паролей.
        changed = run([
            "docker", "exec", container, "sh", "-ec",
            'printf "local all all trust\\nhost all all all trust\\n" > "$PGDATA/pg_hba.conf"',
        ])
        assert changed.returncode == 0, changed.stderr
        sql("SELECT pg_reload_conf()")
        time.sleep(1)
        for mode in ("direct", "job"):
            result = bootstrap(mode, f"{mode}_user", f"{mode}_db", "wrong-test-password")
            assert result.returncode != 0, "Trust должен приводить к ошибке"
        print("OK: оба пути отклоняют trust-аутентификацию")
    finally:
        run(["docker", "stop", container])


if __name__ == "__main__":
    main()
