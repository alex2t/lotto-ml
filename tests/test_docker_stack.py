"""
The Docker stack must order its services and must not write into the repo (F-45).

The production overlay adds the part the internet can reach, so it is checked here too:
Caddy is the only thing publishing a port, and the rebuild receiver - the one network-facing
thing in this repo that writes files - is not proxied to it.

`echo >> Step 1/2: ...` in the `.bat` scripts is a file redirect, not an arrow: cmd wrote four junk
files into the repo root and printed nothing. `docker-compose.yml` expressed the engine-before-web
ordering only inside the start scripts, so a bare `docker compose up` let Streamlit read a
half-written artifact.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

class ComposeLoader(yaml.SafeLoader):
    """
    Compose has its own YAML tags - `!reset` and `!override` - for clearing a value an
    overlay inherits. The safe loader does not know them, so they are constructed as the
    value they wrap: `ports: !reset []` loads as an empty list, which is what it means.
    """


def _tagged(loader, suffix, node):
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    return loader.construct_scalar(node)


ComposeLoader.add_multi_constructor('!', _tagged)


def load_compose(name):
    return yaml.load((REPO_ROOT / name).read_text(), Loader=ComposeLoader)




def test_batch_scripts_echo_instead_of_redirecting():
    """`echo >> text` makes the first word a filename and the rest its contents."""
    for name in ("docker_start.bat", "docker_stop.bat"):
        for line in (REPO_ROOT / "scripts" / name).read_text().splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("echo"):
                assert ">" not in stripped, f"{name}: {stripped}"


def test_web_services_wait_for_a_successful_engine_run():
    """A bare `docker compose up` must not serve an artifact the engine has not finished writing."""
    compose = load_compose("docker-compose.yml")
    for service in ("streamlit-web", "nextjs-web"):
        depends = compose["services"][service]["depends_on"]
        assert depends["data-engine"]["condition"] == "service_completed_successfully"


def test_web_services_mount_the_artifacts_read_only():
    """Only the engine writes data/. Both sites read it."""
    compose = load_compose("docker-compose.yml")
    for service in ("streamlit-web", "nextjs-web"):
        mounts = compose["services"][service]["volumes"]
        assert "./data:/app/data:ro" in mounts


def test_container_uid_is_a_build_arg():
    """The bind mount replaces the image's data/ with the host's, so the uid must be settable."""
    for name in ("Dockerfile.data_engine", "Dockerfile.streamlit", "Dockerfile.web"):
        dockerfile = (REPO_ROOT / name).read_text()
        assert "ARG UID=1000" in dockerfile
        assert "${UID}" in dockerfile
    compose = load_compose("docker-compose.yml")
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
    compose = load_compose("docker-compose.yml")
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


def test_the_openrouter_key_comes_from_secrets_env_not_interpolation():
    """
    The chat panel's key reaches nextjs-web the way the admin secrets do - through the raw
    secrets.env - never `environment:` interpolation, in the base file or the VPS overlay,
    and never as a NEXT_PUBLIC_ variable, which would ship it to the browser (chat.md 8).
    """
    for name in ("docker-compose.yml", "docker-compose.prod.yml"):
        service = load_compose(name)["services"]["nextjs-web"]
        for entry in service.get("environment", []):
            assert "OPENROUTER" not in entry, (name, entry)

    for example in ("secrets.env.example", "frontend/.env.example"):
        lines = (REPO_ROOT / example).read_text().splitlines()
        assert "OPENROUTER_API_KEY=" in lines, example

    frontend = REPO_ROOT / "frontend"
    for source in [*frontend.glob("app/**/*.ts*"), *frontend.glob("lib/**/*.ts*"), *frontend.glob("components/**/*.ts*")]:
        assert "NEXT_PUBLIC_OPENROUTER" not in source.read_text(encoding="utf-8"), source


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

# --- Phase 5: the production overlay ------------------------------------------------------

def prod_compose():
    """The base file with the production overlay applied, as compose would merge them."""
    base = load_compose("docker-compose.yml")
    overlay = load_compose("docker-compose.prod.yml")
    merged = base["services"]
    for name, service in overlay["services"].items():
        merged.setdefault(name, {}).update(service)
    return merged


def test_only_the_proxy_reaches_the_internet():
    """
    The site must not be reachable around the proxy on http://<vps-ip>:3000, where there is
    no TLS and none of the security headers.
    """
    overlay = load_compose("docker-compose.prod.yml")
    services = overlay["services"]

    # compose clears the published ports with a !reset tag, which PyYAML hands back as None.
    assert "ports" in services["nextjs-web"]
    assert not services["nextjs-web"]["ports"]

    published = services["reverse-proxy"]["ports"]
    assert "80:80" in published and "443:443" in published


def test_the_rebuild_receiver_is_not_published_or_proxied():
    """
    It runs drawpick.py on request. n8n reaches it over the Docker network; nothing should
    be able to reach it from outside the VPS.
    """
    overlay = load_compose("docker-compose.prod.yml")
    receiver = overlay["services"]["rebuild-receiver"]
    assert "ports" not in receiver, "the receiver must not publish a port"

    caddyfile = (REPO_ROOT / "reverse_proxy" / "Caddyfile").read_text()
    assert "rebuild" not in caddyfile, "the receiver must not be proxied"
    assert "reverse_proxy nextjs-web:3000" in caddyfile


def test_the_rebuild_secret_comes_from_secrets_env_not_interpolation():
    """The same rule as the admin account: compose expands `$` in a value it substitutes (F-58)."""
    overlay = load_compose("docker-compose.prod.yml")
    receiver = overlay["services"]["rebuild-receiver"]

    assert any(
        entry["path"] == "secrets.env" and entry.get("format") == "raw"
        for entry in receiver["env_file"]
    ), receiver["env_file"]
    for entry in receiver.get("environment", []):
        assert "REBUILD_SECRET" not in entry, entry


def test_the_receiver_never_gets_the_docker_socket():
    """Mounting it would give a network-facing service root on the host."""
    overlay = load_compose("docker-compose.prod.yml")
    for name, service in overlay["services"].items():
        for mount in service.get("volumes", []):
            assert "docker.sock" not in str(mount), (name, mount)


def test_the_receiver_can_write_the_artifacts_and_the_site_cannot():
    overlay = load_compose("docker-compose.prod.yml")
    assert "./data:/app/data:rw" in overlay["services"]["rebuild-receiver"]["volumes"]

    base = load_compose("docker-compose.yml")
    assert "./data:/app/data:ro" in base["services"]["nextjs-web"]["volumes"]


def test_the_engine_image_carries_the_receiver():
    """The receiver runs drawpick.py in-process, so it ships in the engine image."""
    dockerfile = (REPO_ROOT / "Dockerfile.data_engine").read_text()
    assert "COPY rebuild_webhook.py" in dockerfile


def test_the_proxy_sets_the_security_headers_and_keeps_its_certificates():
    caddyfile = (REPO_ROOT / "reverse_proxy" / "Caddyfile").read_text()
    for header in (
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Content-Security-Policy",
        "Referrer-Policy",
    ):
        assert header in caddyfile, header

    overlay = load_compose("docker-compose.prod.yml")
    proxy = overlay["services"]["reverse-proxy"]
    # Losing /data means re-issuing every certificate, and Let's Encrypt rate-limits that.
    assert any("caddy_data:/data" in str(v) for v in proxy["volumes"])


def test_the_proxy_needs_no_plugin_build():
    """
    `rate_limit` and friends are plugins, not standard Caddy. A Caddyfile that needs a custom
    image is one that does not start on `caddy:2-alpine`.
    """
    # Directives only: the file explains in a comment why rate_limit is absent, and a
    # comment is not a directive.
    directives = "\n".join(
        line for line in (REPO_ROOT / "reverse_proxy" / "Caddyfile").read_text().splitlines()
        if not line.strip().startswith("#")
    )
    for plugin in ("rate_limit", "replace_response", "geoip"):
        assert plugin not in directives, plugin

    overlay = load_compose("docker-compose.prod.yml")
    assert overlay["services"]["reverse-proxy"]["image"].startswith("caddy:")
    assert "build" not in overlay["services"]["reverse-proxy"]


def test_an_empty_acme_email_cannot_stop_the_proxy_starting():
    """
    `email {$ACME_EMAIL}` fails to parse when the variable is empty, so a blank line in .env
    would take the site down. Let's Encrypt issues without a contact address.
    """
    caddyfile = (REPO_ROOT / "reverse_proxy" / "Caddyfile").read_text()
    directives = [
        line.strip() for line in caddyfile.splitlines()
        if line.strip().startswith("email ")
    ]
    assert directives == [], directives


def test_the_site_is_health_checked_on_something_that_reads_the_artifacts():
    """
    A process that is listening but cannot see data/ - an unmounted volume, the F-45
    permissions trap - would answer every page with an error.
    """
    caddyfile = (REPO_ROOT / "reverse_proxy" / "Caddyfile").read_text()
    assert "health_uri /api/health" in caddyfile

    route = (REPO_ROOT / "frontend" / "app" / "api" / "health" / "route.ts").read_text(
        encoding="utf-8"
    )
    assert "latestDrawDate" in route
    assert "503" in route
