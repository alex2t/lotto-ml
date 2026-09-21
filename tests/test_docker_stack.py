"""
The Docker stack must order its services and must not write into the repo (F-45).

`echo >> Step 1/2: ...` in the `.bat` scripts is a file redirect, not an arrow: cmd wrote four junk
files into the repo root and printed nothing. `docker-compose.yml` expressed the engine-before-web
ordering only inside the start scripts, so a bare `docker compose up` let Streamlit read a
half-written artifact.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_batch_scripts_echo_instead_of_redirecting():
    """`echo >> text` makes the first word a filename and the rest its contents."""
    for name in ("docker_start.bat", "docker_stop.bat"):
        for line in (REPO_ROOT / "scripts" / name).read_text().splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("echo"):
                assert ">" not in stripped, f"{name}: {stripped}"


def test_web_services_wait_for_a_successful_engine_run():
    """A bare `docker compose up` must not serve an artifact the engine has not finished writing."""
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    for service in ("streamlit-web", "nextjs-web"):
        depends = compose["services"][service]["depends_on"]
        assert depends["data-engine"]["condition"] == "service_completed_successfully"


def test_web_services_mount_the_artifacts_read_only():
    """Only the engine writes data/. Both sites read it."""
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    for service in ("streamlit-web", "nextjs-web"):
        mounts = compose["services"][service]["volumes"]
        assert "./data:/app/data:ro" in mounts


def test_container_uid_is_a_build_arg():
    """The bind mount replaces the image's data/ with the host's, so the uid must be settable."""
    for name in ("Dockerfile.data_engine", "Dockerfile.streamlit", "Dockerfile.web"):
        dockerfile = (REPO_ROOT / name).read_text()
        assert "ARG UID=1000" in dockerfile
        assert "${UID}" in dockerfile
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    for service in ("data-engine", "streamlit-web", "nextjs-web"):
        assert compose["services"][service]["build"]["args"]["UID"] == "${UID:-1000}"


def test_the_web_image_runs_as_the_build_arg_user():
    """A root container would write root-owned files through any future writable mount."""
    dockerfile = (REPO_ROOT / "Dockerfile.web").read_text()
    assert "USER ${UID}:${GID}" in dockerfile


def test_admin_secrets_are_passed_without_interpolation():
    """
    A bcrypt hash always contains `$`, and compose expands `$name` inside an interpolated
    value, so `environment: ADMIN_PASSWORD_HASH=${ADMIN_PASSWORD_HASH}` delivered a mangled
    hash and every login failed with 401 (F-58). The file is `secrets.env`, not `.env`:
    compose reads `.env` for its own substitution, where the same expansion applies.
    """
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text())
    service = compose["services"]["nextjs-web"]

    env_files = service["env_file"]
    assert any(
        entry["path"] == "secrets.env" and entry.get("format") == "raw"
        for entry in env_files
    ), env_files
    assert all(entry["path"] != ".env" for entry in env_files), env_files
    # The file is optional: the public site must start without an admin account.
    assert all(entry.get("required") is False for entry in env_files), env_files

    for entry in service.get("environment", []):
        assert "ADMIN_" not in entry and "SESSION_SECRET" not in entry, entry


def test_the_env_files_are_not_committed_or_shipped():
    """secrets.env holds the admin hash and the session secret."""
    ignored = [line.strip() for line in (REPO_ROOT / ".gitignore").read_text().splitlines()]
    docker_ignored = [
        line.strip() for line in (REPO_ROOT / ".dockerignore").read_text().splitlines()
    ]
    for name in (".env", "secrets.env"):
        assert name in ignored, name
        assert name in docker_ignored, name


def test_the_site_builds_without_the_artifacts():
    """
    data/ is a runtime mount, absent while the image builds, so no route may read an
    artifact at build time - the root layout did, and Next's prerender of /_not-found
    failed with ENOENT on lotto_draw_history.json.
    """
    layout = (REPO_ROOT / "frontend" / "app" / "layout.tsx").read_text(encoding="utf-8")
    assert "lib/data" not in layout, "the root layout must not read an artifact"


def test_data_is_not_sent_to_the_build_context():
    """Neither image copies data/; it is bind-mounted at runtime."""
    ignored = (REPO_ROOT / ".dockerignore").read_text().splitlines()
    assert "data/" in [line.strip() for line in ignored]
    for name in ("Dockerfile.data_engine", "Dockerfile.streamlit", "Dockerfile.web"):
        dockerfile = (REPO_ROOT / name).read_text()
        assert "COPY data" not in dockerfile


def test_the_frontend_build_context_excludes_installed_and_built_output():
    """node_modules and .next come from the image's own npm ci and build, never the host."""
    ignored = [line.strip() for line in (REPO_ROOT / ".dockerignore").read_text().splitlines()]
    for pattern in ("frontend/node_modules/", "frontend/.next/"):
        assert pattern in ignored
