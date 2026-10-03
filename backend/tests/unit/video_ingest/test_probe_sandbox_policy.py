"""Process sandbox policy of the probe stage (ST-009; NFR-054; AQS/SEC-06 13.2.4, AQS/SEC-10).

Pure rules only: which argv ffprobe gets, which URLs it may read, which environment it sees and
which resource limits apply. The integration suite ``tests/integration/video_ingest/
test_probe_sandbox.py`` proves that the limits are enforced on a real child process.
"""

from __future__ import annotations

import pytest

from racket.video_ingest.probe import (
    ProbeFailed,
    ProbeLimits,
    child_environment,
    ffprobe_argv,
)

URL = "http://objectstore:8333/racket-media/originals/0f/abc?X-Amz-Signature=deadbeef"


# ------------------------------------------------------------------ negative cases first
@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "/etc/passwd",
        "concat:http://a/x|http://b/y",
        "subfile,,start,0,end,1,,:http://a/x",
        "ftp://objectstore/x",
        "rtmp://objectstore/live",
        "-i",
        "http://",
        "",
    ],
)
def test_only_http_urls_with_a_host_are_probed(url: str) -> None:
    with pytest.raises(ProbeFailed):
        ffprobe_argv("ffprobe", url)


def test_the_refusal_does_not_echo_the_url() -> None:
    secret = "file:///tmp/X-Amz-Signature=deadbeef"

    with pytest.raises(ProbeFailed) as info:
        ffprobe_argv("ffprobe", secret)

    assert "deadbeef" not in str(info.value)


def test_no_local_file_protocol_is_whitelisted() -> None:
    argv = ffprobe_argv("ffprobe", URL)
    protocols = argv[argv.index("-protocol_whitelist") + 1].split(",")

    assert "file" not in protocols
    assert set(protocols) <= {"http", "https", "tcp", "tls"}


def test_child_environment_carries_no_secrets() -> None:
    parent = {
        "PATH": "/usr/bin",
        "DATABASE_URL": "postgresql://u:p@db/x",
        "S3_SECRET_ACCESS_KEY": "s3cr3t",
        "S3_ACCESS_KEY_ID": "id",
        "AWS_SECRET_ACCESS_KEY": "s3cr3t",
        "HTTP_PROXY": "http://proxy:3128",
        "HTTPS_PROXY": "http://proxy:3128",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "http://tracing:4318",
    }

    env = child_environment(parent)

    assert set(env) <= {"PATH", "LC_ALL"}
    assert "s3cr3t" not in "".join(env.values())


@pytest.mark.parametrize(
    "field",
    ["wall_clock_s", "cpu_s", "memory_bytes", "open_files", "processes", "max_output_bytes"],
)
def test_limits_must_be_positive(field: str) -> None:
    with pytest.raises(ValueError, match=f"{field} must be positive"):
        ProbeLimits(**{field: 0})


# ------------------------------------------------------------------ positive cases
@pytest.mark.parametrize(
    "url",
    [URL, "https://s3.eu-west-1.amazonaws.com/racket-media/originals/x?X-Amz-Signature=1"],
)
def test_the_server_generated_url_is_the_only_input(url: str) -> None:
    argv = ffprobe_argv("/opt/ffmpeg/bin/ffprobe", url)

    assert argv[0] == "/opt/ffmpeg/bin/ffprobe"
    assert argv[-1] == url
    assert argv.count(url) == 1
    assert argv[1:-1] == ffprobe_argv("ffprobe", URL)[1:-1]  # nothing else varies


def test_ffprobe_is_told_to_print_json_streams_and_format_only() -> None:
    argv = ffprobe_argv("ffprobe", URL)

    for flag in ("-show_format", "-show_streams"):
        assert flag in argv
    assert argv[argv.index("-print_format") + 1] == "json"
    assert "-show_frames" not in argv
    assert "-show_packets" not in argv


def test_default_limits_are_bounded() -> None:
    limits = ProbeLimits()

    assert limits.wall_clock_s <= 120
    assert limits.cpu_s <= limits.wall_clock_s
    assert limits.memory_bytes <= 2 * 1024**3  # inside the 2 GB container limit
    assert limits.file_size_bytes == 0  # ffprobe never needs to write a file
