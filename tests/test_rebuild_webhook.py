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

HEADER = 'Date,Num1,Num2,Num3,Num4,Num5,Num6,Bonus'
EXISTING = ['16 Sep 2026,04,07,19,20,35,42,31', '14 Sep 2026,02,09,18,26,33,40,11']
NEW_DRAW = {'date': '2026-09-19', 'main': [44, 10, 28, 11, 41, 20], 'bonus': 2}
NEW_DRAW_ROW = '19 Sep 2026,10,11,20,28,41,44,02'


def seed_csv(root, rows=EXISTING):
    """The CSV as the VPS holds it: newest-first, LF endings."""
    path = root / 'data' / 'irish500.csv'
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write('\n'.join([HEADER] + list(rows)) + '\n')
    return path


def body_for(draw=NEW_DRAW):
    return json.dumps(draw).encode()


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

    seed_csv(tmp_path)
    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]

    yield f'http://127.0.0.1:{port}', calls, tmp_path

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
    url, calls, root = receiver
    body = body_for()

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'rebuilt'
    assert len(calls) == 1


def test_an_unsigned_request_is_refused_and_runs_nothing(receiver):
    url, calls, root = receiver
    status, payload = post(url, body_for())
    assert status == 401
    assert payload == {'error': 'bad signature'}
    assert calls == []


def test_a_wrong_secret_is_refused(receiver):
    url, calls, root = receiver
    body = b'{}'
    status, _ = post(url, body, sign(body, b'a-different-secret-entirely'))
    assert status == 401
    assert calls == []


def test_a_signature_over_different_content_is_refused(receiver):
    """
    The signature covers the body that was actually posted. Signing one payload and sending
    another is exactly what a replay looks like.
    """
    url, calls, root = receiver
    status, _ = post(url, b'{"draw": "tampered"}', sign(b'{"draw": "original"}'))
    assert status == 401
    assert calls == []


def test_only_the_rebuild_path_accepts_a_post(receiver):
    url, calls, root = receiver
    body = b'{}'
    request = urllib.request.Request(url + '/anything', data=body, method='POST')
    request.add_header(rebuild_webhook.SIGNATURE_HEADER, sign(body))
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=30)
    assert error.value.code == 404
    assert calls == []


def test_the_health_endpoint_needs_no_signature_and_runs_nothing(receiver):
    url, calls, root = receiver
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

    seed_csv(tmp_path)
    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}'

    first_result = {}

    def first_call():
        first_result['status'], first_result['payload'] = post(url, body_for(), sign(body_for()))

    first = threading.Thread(target=first_call)
    first.start()
    assert started.wait(timeout=10), 'the first rebuild never started'

    try:
        status, payload = post(url, body_for(), sign(body_for()))
        assert status == 409
        assert 'already running' in payload['error']
    finally:
        release.set()
        first.join(timeout=30)
        server.shutdown()
        server.server_close()

    assert first_result['status'] == 200


def test_the_lock_is_released_so_a_later_rebuild_can_run(receiver):
    url, calls, root = receiver
    for _ in range(3):
        status, _ = post(url, body_for(), sign(body_for()))
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
    seed_csv(tmp_path)
    server = rebuild_webhook.serve('127.0.0.1', 0, str(tmp_path), SECRET)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_address[1]}'

    try:
        status, payload = post(url, body_for(), sign(body_for()))
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
    url, calls, root = receiver
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
    url, calls, root = receiver
    for sent in ('', 'ab', 'z' * 64, 'not-hex-at-all'):
        status, _ = post(url, body_for(), sent)
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
    url, _, root = receiver
    status, payload = post(url, body_for(), sign(body_for()))
    assert status == 200
    assert isinstance(payload['seconds'], (int, float))


# The draw in the body: appending it, recognising it again, and rebuilding when the
# artifacts are older than the CSV. nextStep/lottodraw.md sections 3 and 4.


def artifacts_fresh(root):
    """Write every artifact drawpick.py is expected to produce, newer than the CSV."""
    for relative in rebuild_webhook.expected_artifacts():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}', encoding='utf-8')


def test_a_new_draw_is_appended_after_the_header_and_rebuilds(receiver):
    url, calls, root = receiver
    body = body_for()

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'rebuilt'
    assert payload['appended'] is True
    assert payload['draw'] == '2026-09-19'
    assert payload['csv_rows'] == len(EXISTING) + 1
    assert len(calls) == 1

    raw = (root / 'data' / 'irish500.csv').read_bytes()
    assert b'\r\n' not in raw, 'the CSV is stored LF (F-44)'
    lines = raw.decode().rstrip('\n').split('\n')
    assert lines[0] == HEADER
    assert lines[1] == '19 Sep 2026,10,11,20,28,41,44,02'
    assert lines[2:] == EXISTING


def test_the_same_draw_twice_appends_once_and_rebuilds_once(receiver):
    url, calls, root = receiver
    body = body_for()

    post(url, body, sign(body))
    artifacts_fresh(root)

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'already had it'
    assert payload['appended'] is False
    assert payload['csv_rows'] == len(EXISTING) + 1
    assert len(calls) == 1, 'a retried webhook must cost nothing'


@pytest.mark.parametrize('draw, why', [
    ({**NEW_DRAW, 'main': [44, 10, 28, 11, 41, 3]}, 'a main number differs'),
    ({**NEW_DRAW, 'bonus': 9}, 'the bonus differs'),
])
def test_a_known_date_with_other_numbers_is_a_conflict_not_a_success(receiver, draw, why):
    """
    F-72: the date alone once decided "already had it", so a misread draw on a date the file
    held was answered as a success and n8n never sent its failure email. The row in the file
    stays; the caller is told the two disagree, and nothing is rebuilt - not even stale
    artifacts, since which row is right is not known.
    """
    url, calls, root = receiver
    path = seed_csv(root, [NEW_DRAW_ROW] + EXISTING)
    before = path.read_bytes()
    body = body_for(draw)

    status, payload = post(url, body, sign(body))

    assert status == 409, why
    assert payload['state'] == 'conflict'
    assert payload['appended'] is False
    assert payload['in_csv'] == {'main': [10, 11, 20, 28, 41, 44], 'bonus': 2}
    assert payload['posted'] == {'main': sorted(draw['main']), 'bonus': draw['bonus']}
    assert path.read_bytes() == before
    assert calls == []


def test_a_known_draw_in_another_order_is_still_the_same_draw(receiver):
    url, calls, root = receiver
    seed_csv(root, [NEW_DRAW_ROW] + EXISTING)
    artifacts_fresh(root)
    body = body_for({**NEW_DRAW, 'main': sorted(NEW_DRAW['main'], reverse=True)})

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'already had it'
    assert calls == []


def test_a_retry_rebuilds_when_the_artifacts_are_older_than_the_csv(receiver):
    """
    The append succeeded and the engine then failed, so the row is in the file and the
    artifacts are stale. Posting the same draw again is the repair.
    """
    url, calls, root = receiver
    body = body_for()

    artifacts_fresh(root)
    time.sleep(0.01)
    seed_csv(root, [NEW_DRAW_ROW] + EXISTING)

    status, payload = post(url, body, sign(body))

    assert status == 200
    assert payload['state'] == 'rebuilt stale artifacts'
    assert payload['appended'] is False
    assert payload['csv_rows'] == len(EXISTING) + 1
    assert len(calls) == 1


@pytest.mark.parametrize('draw, why', [
    ({'date': '19 Sep 2026', 'main': [1, 2, 3, 4, 5, 6], 'bonus': 7}, 'not ISO'),
    ({'date': '2099-01-01', 'main': [1, 2, 3, 4, 5, 6], 'bonus': 7}, 'in the future'),
    ({'date': '2026-09-01', 'main': [1, 2, 3, 4, 5, 6], 'bonus': 7}, 'older than the newest row'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5], 'bonus': 7}, 'five numbers'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5, 5], 'bonus': 7}, 'a repeated number'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5, 48], 'bonus': 7}, 'out of range'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5, 6], 'bonus': 6}, 'bonus among the main'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5, 6], 'bonus': 0}, 'bonus out of range'),
    ({'date': '2026-09-19', 'main': [1, 2, 3, 4, 5, 6]}, 'no bonus'),
])
def test_a_malformed_draw_is_rejected_and_writes_nothing(receiver, draw, why):
    url, calls, root = receiver
    path = root / 'data' / 'irish500.csv'
    before = path.read_bytes()
    body = body_for(draw)

    status, payload = post(url, body, sign(body))

    assert status == 400, why
    assert payload['state'] == 'rejected'
    assert calls == []
    assert path.read_bytes() == before


def test_a_body_that_is_not_json_is_rejected(receiver):
    url, calls, root = receiver
    status, payload = post(url, b'not json at all', sign(b'not json at all'))
    assert status == 400
    assert payload['state'] == 'rejected'
    assert calls == []


def test_the_csv_is_replaced_atomically(monkeypatch, tmp_path):
    """
    A crash partway through leaves the original file intact, not a truncated one that
    drawpick.py would read without complaint.
    """
    path = seed_csv(tmp_path)
    original = path.read_bytes()

    def crash(source, destination):
        raise OSError('interrupted before the rename')

    monkeypatch.setattr(rebuild_webhook.os, 'replace', crash)
    draw = rebuild_webhook.parse_draw(body_for())
    with pytest.raises(OSError):
        rebuild_webhook.append_draw(path, draw, rebuild_webhook.csv_lines(path))

    assert path.read_bytes() == original


def test_the_iso_date_becomes_the_format_the_file_holds():
    """One place knows the file's format; n8n only ever sends ISO."""
    draw = rebuild_webhook.parse_draw(
        body_for({'date': '2026-09-05', 'main': [8, 11, 15, 21, 33, 44], 'bonus': 14})
    )
    assert rebuild_webhook.format_row(draw) == '05 Sep 2026,08,11,15,21,33,44,14'


def test_the_engine_log_is_decoded_as_utf8(monkeypatch, tmp_path):
    """
    drawpick.py prints emoji. text=True decodes with the locale codec - cp1252 on Windows -
    which raises on the first one and leaves stdout as None, so a rebuild that worked is
    reported as a crash.
    """
    seen = {}

    class Finished:
        returncode = 0
        stdout = 'done'
        stderr = ''

    def capture(cmd, **kwargs):
        seen.update(kwargs)
        return Finished()

    monkeypatch.setattr(rebuild_webhook.subprocess, 'run', capture)
    rebuild_webhook.run_drawpick(str(tmp_path))

    assert seen['encoding'] == 'utf-8'
    assert seen['errors'] == 'replace'
