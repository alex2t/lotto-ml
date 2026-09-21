"""
The rebuild receiver: the thing on the VPS that n8n asks to rewrite the artifacts.

It runs `drawpick.py` in its own process, so it is the only network-facing code in this repo
that causes anything to be written. Everything here is about that: who is allowed to ask,
what happens when two ask at once, and what it says when the engine fails.

`drawpick.py` itself is never run here - these tests point the receiver at a stub so they
stay fast and deterministic. That the real engine works is `tests/test_pipeline_completeness.py`.
"""

import hashlib
import hmac
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

import rebuild_webhook

SECRET = b'a-secret-at-least-sixteen-chars'


def sign(body: bytes, key: bytes = SECRET) -> str:
    return hmac.new(key, body, hashlib.sha256).hexdigest()


@pytest.fixture
def receiver(monkeypatch, tmp_path):
    """A running receiver whose 'engine' is a stub we control."""
    calls = []

    def fake_run(repo_root):
        calls.append(repo_root)
        return {'state': 'ok', 'seconds': 0.1, 'exit_code': 0}

    monkeypatch.setattr(rebuild_webhook, 'run_drawpick', fake_run)

    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    yield f'http://127.0.0.1:{port}', calls

    server.shutdown()
    server.server_close()


def post(url, body=b'{}', signature=None, header=rebuild_webhook.SIGNATURE_HEADER):
    request = urllib.request.Request(url + rebuild_webhook.PATH, data=body, method='POST')
    if signature is not None:
        request.add_header(header, signature)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_a_correctly_signed_request_runs_the_engine(receiver):
    url, calls = receiver
    body = json.dumps({'draw': '2026-09-19'}).encode()

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'ok'
    assert len(calls) == 1


def test_an_unsigned_request_is_refused_and_runs_nothing(receiver):
    url, calls = receiver
    status, payload = post(url, b'{}')
    assert status == 401
    assert payload == {'error': 'bad signature'}
    assert calls == []


def test_a_wrong_secret_is_refused(receiver):
    url, calls = receiver
    body = b'{}'
    status, _ = post(url, body, sign(body, b'a-different-secret-entirely'))
    assert status == 401
    assert calls == []


def test_a_signature_over_different_content_is_refused(receiver):
    """
    The signature covers the body that was actually posted. Signing one payload and sending
    another is exactly what a replay looks like.
    """
    url, calls = receiver
    status, _ = post(url, b'{"draw": "tampered"}', sign(b'{"draw": "original"}'))
    assert status == 401
    assert calls == []


def test_only_the_rebuild_path_accepts_a_post(receiver):
    url, calls = receiver
    body = b'{}'
    request = urllib.request.Request(url + '/anything', data=body, method='POST')
    request.add_header(rebuild_webhook.SIGNATURE_HEADER, sign(body))
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=30)
    assert error.value.code == 404
    assert calls == []


def test_the_health_endpoint_needs_no_signature_and_runs_nothing(receiver):
    url, calls = receiver
    with urllib.request.urlopen(url + '/health', timeout=30) as response:
        payload = json.loads(response.read())
    assert response.status == 200
    assert payload['state'] == 'listening'
    assert calls == []


def test_two_rebuilds_at_once_are_refused_not_queued(monkeypatch, tmp_path):
    """
    A rebuild rewrites the files the site is reading and takes about a minute. Two at once
    would interleave writes, so the second is turned away rather than run.
    """
    started = threading.Event()
    release = threading.Event()

    def slow_run(repo_root):
        started.set()
        release.wait(timeout=30)
        return {'state': 'ok', 'seconds': 1.0, 'exit_code': 0}

    monkeypatch.setattr(rebuild_webhook, 'run_drawpick', slow_run)

    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}'

    first_result = {}

    def first_call():
        first_result['status'], first_result['payload'] = post(url, b'{}', sign(b'{}'))

    first = threading.Thread(target=first_call)
    first.start()
    assert started.wait(timeout=10), 'the first rebuild never started'

    try:
        status, payload = post(url, b'{}', sign(b'{}'))
        assert status == 409
        assert 'already running' in payload['error']
    finally:
        release.set()
        first.join(timeout=30)
        server.shutdown()
        server.server_close()

    assert first_result['status'] == 200


def test_the_lock_is_released_so_a_later_rebuild_can_run(receiver):
    url, calls = receiver
    for _ in range(3):
        status, _ = post(url, b'{}', sign(b'{}'))
        assert status == 200
    assert len(calls) == 3


def test_a_failing_engine_answers_500_with_the_tail_of_its_log(monkeypatch, tmp_path):
    """n8n's failure email needs to say what broke, not just that something did."""
    def failing_run(repo_root):
        return {
            'state': 'failed',
            'seconds': 2.0,
            'exit_code': 1,
            'tail': ['Phase 16 raised', 'INCOMPLETE'],
            'stderr_tail': ['ModuleNotFoundError: sklearn'],
        }

    monkeypatch.setattr(rebuild_webhook, 'run_drawpick', failing_run)
    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}'

    try:
        status, payload = post(url, b'{}', sign(b'{}'))
        assert status == 500
        assert payload['state'] == 'failed'
        assert payload['exit_code'] == 1
        assert 'ModuleNotFoundError: sklearn' in payload['stderr_tail']
    finally:
        server.shutdown()
        server.server_close()


def test_an_oversized_body_is_refused_before_it_is_read(receiver):
    """
    The receiver replies 413 without reading the body, so a client still sending may see the
    connection reset rather than the response. That is the point - the bytes are never
    buffered - so this asserts what matters: the engine did not run.
    """
    url, calls = receiver
    body = b'x' * (rebuild_webhook.MAX_BODY_BYTES + 1)
    try:
        status, _ = post(url, body, sign(body))
        assert status == 413
    except (ConnectionResetError, urllib.error.URLError) as error:
        # A reset while the oversized body was still going out.
        assert isinstance(error, (ConnectionResetError, urllib.error.URLError))
    assert calls == []


def test_it_refuses_to_start_without_a_long_enough_secret(monkeypatch):
    """A receiver that runs the engine for anyone is worse than one that does not run."""
    monkeypatch.delenv('REBUILD_SECRET', raising=False)
    with pytest.raises(SystemExit):
        rebuild_webhook.secret()

    monkeypatch.setenv('REBUILD_SECRET', 'too-short')
    with pytest.raises(SystemExit):
        rebuild_webhook.secret()

    monkeypatch.setenv('REBUILD_SECRET', 'x' * 16)
    assert rebuild_webhook.secret() == b'x' * 16


def test_signature_comparison_does_not_leak_its_length(receiver):
    """A wrong-length signature is a mismatch, not a crash."""
    url, calls = receiver
    for sent in ('', 'ab', 'z' * 64, 'not-hex-at-all'):
        status, _ = post(url, b'{}', sent)
        assert status == 401
    assert calls == []


def test_run_drawpick_reports_a_timeout_rather_than_hanging(monkeypatch, tmp_path):
    """A hung engine must not hold the lock for ever."""
    import subprocess

    def timing_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd='drawpick.py', timeout=1)

    monkeypatch.setattr(rebuild_webhook.subprocess, 'run', timing_out)
    result = rebuild_webhook.run_drawpick(str(tmp_path))
    assert result['state'] == 'timed out'
    assert result['exit_code'] is None


def test_run_drawpick_runs_the_engine_in_the_directory_it_is_given(monkeypatch, tmp_path):
    """
    drawpick.py resolves data/ relative to the working directory, so the receiver must run
    it where the mounted data lives, not wherever the process happens to start.
    """
    seen = {}

    class Finished:
        returncode = 0
        stdout = 'ok'
        stderr = ''

    def capture(cmd, cwd, **kwargs):
        seen['cmd'] = cmd
        seen['cwd'] = cwd
        return Finished()

    monkeypatch.setattr(rebuild_webhook.subprocess, 'run', capture)
    rebuild_webhook.run_drawpick(str(tmp_path))

    assert seen['cwd'] == str(tmp_path)
    assert seen['cmd'][1] == 'drawpick.py'


def test_the_engine_is_never_run_through_a_shell(monkeypatch, tmp_path):
    """
    Nothing from the request reaches the command, and it is a list rather than a string, so
    there is no shell to inject into.
    """
    class Finished:
        returncode = 0
        stdout = ''
        stderr = ''

    calls = {}

    def capture(cmd, **kwargs):
        calls['cmd'] = cmd
        calls['shell'] = kwargs.get('shell', False)
        return Finished()

    monkeypatch.setattr(rebuild_webhook.subprocess, 'run', capture)
    rebuild_webhook.run_drawpick(str(tmp_path))

    assert isinstance(calls['cmd'], list)
    assert calls['shell'] is False


def test_the_time_it_took_is_reported(receiver):
    url, _ = receiver
    status, payload = post(url, b'{}', sign(b'{}'))
    assert status == 200
    assert isinstance(payload['seconds'], (int, float))
