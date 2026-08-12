from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def _read_text(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _first(paths: list[Path]) -> Path | None:
    return paths[0] if paths else None


def _relative(path: Path | None, root: Path) -> str | None:
    return path.relative_to(root).as_posix() if path else None


def _prepare_run(base_path: Path, config: dict[str, Any], case_id: str) -> tuple[Path, Path]:
    evals_dir = base_path
    repo_root = evals_dir.parent
    fixture = (evals_dir / config["fixtureProject"]).resolve()
    runs_dir = (evals_dir / config.get("runsDir", ".runs")).resolve()
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{case_id}-{os.getpid()}"
    run_dir = runs_dir / run_id
    project_dir = run_dir / "project"

    if not fixture.is_dir():
        raise FileNotFoundError(f"评测 fixture 不存在: {fixture}")

    runs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(fixture, project_dir)
    shutil.copytree(repo_root / "skills", project_dir / "skills")
    return run_dir, project_dir


def _collect_trace(stdout: str) -> dict[str, Any]:
    event_types: Counter[str] = Counter()
    commands: list[str] = []
    parse_errors = 0

    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            parse_errors += 1
            continue

        event_type = str(event.get("type", "unknown"))
        event_types[event_type] += 1
        payload = json.dumps(event, ensure_ascii=False)
        if "command" in payload.lower() and len(commands) < 50:
            commands.append(payload[:1000])

    return {
        "eventTypes": dict(event_types),
        "commandEvents": commands,
        "jsonParseErrors": parse_errors,
    }


def _collect_artifacts(project_dir: Path, feature_dir: str) -> dict[str, Any]:
    feature_root = project_dir / "prd" / feature_dir
    output_dir = feature_root / "output"
    cases_dir = output_dir / "test-cases"

    analysis_path = _first(sorted(output_dir.glob("*-analysis.md"))) if output_dir.is_dir() else None
    clarifications_path = (
        _first(sorted(output_dir.glob("*-clarifications.md"))) if output_dir.is_dir() else None
    )
    progress_path = cases_dir / "_progress.md"
    summary_path = cases_dir / "test-case-summary.md"
    testcase_paths = []
    if cases_dir.is_dir():
        testcase_paths = [
            path
            for path in sorted(cases_dir.rglob("*.md"))
            if path.name not in {"_progress.md", "test-case-summary.md", "review-report.md"}
        ]

    all_files = [path for path in sorted(project_dir.rglob("*")) if path.is_file()]
    binary_exports = [
        path
        for path in all_files
        if path.suffix.lower() in {".xlsx", ".xls", ".xmind"}
    ]
    global_case_changes = [
        path
        for path in all_files
        if path.is_relative_to(project_dir / "test-cases") and path.name != "index.md"
    ]

    return {
        "analysis": {
            "exists": bool(analysis_path),
            "path": _relative(analysis_path, project_dir),
            "content": _read_text(analysis_path),
        },
        "clarifications": {
            "exists": bool(clarifications_path),
            "path": _relative(clarifications_path, project_dir),
            "content": _read_text(clarifications_path),
        },
        "progress": {
            "exists": progress_path.is_file(),
            "path": _relative(progress_path if progress_path.is_file() else None, project_dir),
            "content": _read_text(progress_path),
        },
        "summary": {
            "exists": summary_path.is_file(),
            "path": _relative(summary_path if summary_path.is_file() else None, project_dir),
            "content": _read_text(summary_path),
        },
        "testCases": [
            {
                "path": path.relative_to(project_dir).as_posix(),
                "content": _read_text(path),
            }
            for path in testcase_paths
        ],
        "binaryExports": [path.relative_to(project_dir).as_posix() for path in binary_exports],
        "globalCaseLibraryChanges": [
            path.relative_to(project_dir).as_posix() for path in global_case_changes
        ],
        "allFiles": [path.relative_to(project_dir).as_posix() for path in all_files],
    }


def _log(message: str) -> None:
    print(f"INFO qa-workflow-provider: {message}", file=sys.stderr, flush=True)


def _last_event_type(events_path: Path) -> str:
    if not events_path.is_file() or events_path.stat().st_size == 0:
        return "none"
    try:
        with events_path.open("rb") as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 65536))
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                return str(json.loads(line).get("type", "unknown"))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return "unknown"


def _last_log_line(path: Path, limit: int = 240) -> str:
    if not path.is_file() or path.stat().st_size == 0:
        return "none"
    try:
        with path.open("rb") as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 8192))
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        if lines:
            return lines[-1].strip()[-limit:] or "none"
    except OSError:
        pass
    return "unavailable"


def _terminate_process_group(process: subprocess.Popen[Any], grace_seconds: int = 10) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=grace_seconds)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def call_api(prompt: str, options: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    config = options.get("config", {})
    base_path = Path(config.get("basePath", ".")).resolve()
    vars_ = context.get("vars", {})
    case_id = str(vars_.get("case_id", "case"))
    feature_dir = str(vars_.get("feature_dir", ""))
    timeout_seconds = int(config.get("timeoutSeconds", 1200))

    started = time.monotonic()
    try:
        run_dir, project_dir = _prepare_run(base_path, config, case_id)
    except Exception as exc:
        return {"output": {"run": {"exitCode": -1, "error": str(exc)}, "artifacts": {}}}

    images = sorted((project_dir / "prd" / feature_dir / "images").glob("*.png"))
    command = [
        os.environ.get("CODEX_BIN", "codex"),
        "-a",
        "never",
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--json",
        "--color",
        "never",
        "-s",
        "workspace-write",
        "-C",
        str(project_dir),
    ]
    model = os.environ.get("CODEX_EVAL_MODEL") or config.get("model")
    if model:
        command.extend(["-m", model])
    for image in images:
        command.extend(["-i", str(image)])
    # `--image` accepts multiple values, so terminate option parsing explicitly.
    # Passing `-` as the positional prompt makes Codex read the prompt from stdin.
    command.extend(["--", "-"])

    events_path = run_dir / "codex-events.jsonl"
    stderr_path = run_dir / "codex-stderr.log"
    run_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_path = run_dir / "provider-diagnostics.log"
    heartbeat_seconds = max(5, int(config.get("heartbeatSeconds", 30)))

    stdout = ""
    stderr = ""
    exit_code = -1
    error = None
    process: subprocess.Popen[Any] | None = None
    try:
        with (
            events_path.open("w", encoding="utf-8") as events_stream,
            stderr_path.open("w", encoding="utf-8") as stderr_stream,
            diagnostic_path.open("w", encoding="utf-8") as diagnostic_stream,
        ):
            diagnostic_stream.write(
                json.dumps(
                    {
                        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        "cwd": str(project_dir),
                        "model": model,
                        "timeoutSeconds": timeout_seconds,
                        "heartbeatSeconds": heartbeat_seconds,
                        "imageCount": len(images),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            diagnostic_stream.flush()
            process = subprocess.Popen(
                command,
                cwd=project_dir,
                stdin=subprocess.PIPE,
                stdout=events_stream,
                stderr=stderr_stream,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=True,
            )
            if process.stdin is None:
                raise RuntimeError("无法打开 Codex stdin")
            process.stdin.write(prompt)
            process.stdin.close()
            _log(
                f"started case={case_id} pid={process.pid} model={model or 'default'} "
                f"timeout={timeout_seconds}s runDir={run_dir}"
            )
            deadline = time.monotonic() + timeout_seconds
            next_heartbeat = time.monotonic() + heartbeat_seconds
            while process.poll() is None:
                now = time.monotonic()
                if now >= deadline:
                    error = f"Codex 执行超过 {timeout_seconds} 秒"
                    exit_code = 124
                    _log(f"timeout case={case_id}; terminating process group pid={process.pid}")
                    _terminate_process_group(process)
                    break
                if now >= next_heartbeat:
                    elapsed = round(now - started)
                    event_bytes = events_path.stat().st_size
                    stderr_bytes = stderr_path.stat().st_size
                    artifact_count = sum(1 for path in project_dir.rglob("*") if path.is_file())
                    heartbeat = (
                        f"heartbeat case={case_id} elapsed={elapsed}s pid={process.pid} "
                        f"events={event_bytes}B stderr={stderr_bytes}B "
                        f"lastEvent={_last_event_type(events_path)} files={artifact_count} "
                        f"stderrTail={json.dumps(_last_log_line(stderr_path), ensure_ascii=False)}"
                    )
                    _log(heartbeat)
                    diagnostic_stream.write(heartbeat + "\n")
                    diagnostic_stream.flush()
                    next_heartbeat = now + heartbeat_seconds
                time.sleep(1)
            if exit_code != 124:
                exit_code = process.returncode
            diagnostic_stream.write(
                f"finished elapsed={round(time.monotonic() - started)}s exitCode={exit_code}\n"
            )
            diagnostic_stream.flush()
    except Exception as exc:
        error = str(exc)
        if process is not None:
            _terminate_process_group(process)

    stdout = _read_text(events_path)
    stderr = _read_text(stderr_path)
    artifacts = _collect_artifacts(project_dir, feature_dir)
    duration_ms = round((time.monotonic() - started) * 1000)

    output = {
        "run": {
            "caseId": case_id,
            "exitCode": exit_code,
            "durationMs": duration_ms,
            "error": error,
            "runDir": str(run_dir),
            "projectDir": str(project_dir),
            "stderrTail": stderr[-6000:],
        },
        "trace": _collect_trace(stdout),
        "artifacts": artifacts,
    }
    return {
        "output": output,
        "latencyMs": duration_ms,
        "metadata": {"runDir": str(run_dir), "caseId": case_id},
    }
