"""Тесты скрипта чистки реестра (roles/k8s/docker-registry-cleanup).

Фейковый Registry v2 на stdlib http.server проверяет обработку призрачных
тегов (tag-link без манифеста, HTTP 404): скрипт обязан снимать такой тег
DELETE по имени, не считая его ошибкой, и завершаться с кодом 0.
"""

import json
import os
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
SCRIPT = REPOSITORY / "roles/k8s/docker-registry-cleanup/files/registry_cleanup.py"

MANIFEST_MEDIA_TYPE = "application/vnd.docker.distribution.manifest.v2+json"
OLD_CREATED = "2026-01-01T00:00:00Z"


class FakeRegistryHandler(BaseHTTPRequestHandler):
    """Реестр с одним репо: latest (защищён), new/old (живые), ghost (404)."""

    deleted_by_tag = []
    deleted_by_digest = []
    now_created = "2026-11-05T00:00:00Z"  # свежая дата для тега new (KEEP_DAYS не срабатывает)

    def log_message(self, format, *args):  # noqa: A002 - сигнатура базового класса
        pass

    def _send(self, status, payload=None, digest=None, link=None):
        body = b"" if payload is None else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        if digest:
            self.send_header("Docker-Content-Digest", digest)
        if link:
            self.send_header("Link", link)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v2/_catalog?n=1000":
            self._send(200, {"repositories": ["app"]})
            return
        if self.path == "/v2/app/tags/list?n=1000":
            self._send(200, {"tags": ["latest", "new", "old", "ghost"]})
            return
        if self.path == "/v2/app/manifests/latest":
            self._send(200, self._manifest(), digest="sha256:latest")
            return
        if self.path == "/v2/app/manifests/new":
            self._send(200, self._manifest("sha256:config-new"), digest="sha256:new")
            return
        if self.path == "/v2/app/manifests/old":
            self._send(200, self._manifest("sha256:config-old"), digest="sha256:old")
            return
        if self.path == "/v2/app/manifests/ghost":
            # tag-link есть, манифеста нет — призрачный тег
            self._send(404, {"errors": [{"code": "MANIFEST_UNKNOWN"}]})
            return
        if self.path == "/v2/app/blobs/sha256:config-new":
            self._send(200, {"created": FakeRegistryHandler.now_created})
            return
        if self.path == "/v2/app/blobs/sha256:config-old":
            self._send(200, {"created": OLD_CREATED})
            return
        self._send(404)

    def do_DELETE(self):
        if self.path == "/v2/app/manifests/ghost":
            FakeRegistryHandler.deleted_by_tag.append(self.path)
            self._send(202)
            return
        if self.path == "/v2/app/manifests/sha256:old":
            FakeRegistryHandler.deleted_by_digest.append(self.path)
            self._send(202)
            return
        self._send(404)

    @staticmethod
    def _manifest(config_digest="sha256:config-old"):
        return {
            "schemaVersion": 2,
            "mediaType": MANIFEST_MEDIA_TYPE,
            "config": {"digest": config_digest, "mediaType": "application/vnd.docker.container.image.v1+json"},
        }


class RegistryCleanupScriptTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeRegistryHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _run(self, extra_env=None):
        environment = os.environ.copy()
        environment.update(
            {
                "REGISTRY_URL": "http://127.0.0.1:{}".format(self.port),
                "KEEP_TAGS": "latest",
                "KEEP_TAG_PATTERNS": "",
                "KEEP_MIN_PER_REPO": "1",
                "KEEP_DAYS": "7",
                "DRY_RUN": "false",
                "REQUEST_TIMEOUT": "10",
            }
        )
        environment.update(extra_env or {})
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=environment,
            timeout=60,
        )

    def test_ghost_tag_untagged_without_error(self):
        FakeRegistryHandler.deleted_by_tag = []
        FakeRegistryHandler.deleted_by_digest = []
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("снят призрачный тег ghost", result.stdout)
        self.assertEqual(FakeRegistryHandler.deleted_by_tag, ["/v2/app/manifests/ghost"])
        # старый незащищённый тег удалён по digest, latest защищён
        self.assertEqual(FakeRegistryHandler.deleted_by_digest, ["/v2/app/manifests/sha256:old"])
        self.assertIn("призрачных тегов снято: 1", result.stdout)
        self.assertIn("ошибок: 0", result.stdout)

    def test_ghost_tag_dry_run_does_not_delete(self):
        FakeRegistryHandler.deleted_by_tag = []
        FakeRegistryHandler.deleted_by_digest = []
        result = self._run({"DRY_RUN": "true"})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[dry-run] снят был бы призрачный тег ghost", result.stdout)
        self.assertEqual(FakeRegistryHandler.deleted_by_tag, [])
        self.assertEqual(FakeRegistryHandler.deleted_by_digest, [])


if __name__ == "__main__":
    unittest.main()
