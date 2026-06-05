from __future__ import annotations

import contextlib
import os
from pathlib import Path
from typing import Any

from decision_layer.slopcodebench import (
    extract_decisions_from_spec,
    format_decision_brief,
    load_json_list,
    merge_decisions,
    save_json,
)


def _decision_root(problem_dir: Path) -> Path:
    return problem_dir / "decision_layer"


def _active_path(problem_dir: Path) -> Path:
    return _decision_root(problem_dir) / "active_decisions.json"


def _checkpoint_decisions_path(problem_dir: Path, checkpoint_name: str) -> Path:
    return _decision_root(problem_dir) / "checkpoint_decisions" / f"{checkpoint_name}.json"


def _prompt_decisions_path(problem_dir: Path, checkpoint_name: str) -> Path:
    return _decision_root(problem_dir) / "prompt_decisions" / f"{checkpoint_name}.json"


def _load_active(problem_dir: Path) -> list[str]:
    return load_json_list(_active_path(problem_dir))


def _load_prompt_decisions(problem_dir: Path, checkpoint_name: str) -> list[str]:
    return load_json_list(_prompt_decisions_path(problem_dir, checkpoint_name))


def _max_decisions_per_checkpoint() -> int:
    raw = os.environ.get("MEMORYCORE_SLOPCODE_MAX_DECISIONS_PER_CHECKPOINT", "24")
    try:
        value = int(raw)
    except ValueError:
        return 24
    return max(1, value)


def _prepend_brief(prompt: str, decisions: list[str]) -> str:
    brief = format_decision_brief(decisions)
    if not brief:
        return prompt
    return f"{brief}\n\n{prompt}"


def _patch_resume_prompt_validation() -> None:
    import slop_code.agent_runner.resume as resume

    if getattr(resume, "_memorycore_d1_patched", False):
        return

    def check_prompt_mismatch(
        problem_config: Any,
        checkpoint_dir: Path,
        checkpoint_name: str,
        checkpoint_names: list[str],
        prompt_template: str,
        environment: Any,
        entry_file: str,
        checkpoints: list[Any],
    ) -> bool:
        prompt_path = checkpoint_dir / resume.PROMPT_FILENAME
        if not prompt_path.exists():
            return False

        try:
            saved_prompt = prompt_path.read_text()
        except OSError:
            return False

        checkpoint_config = next(
            (item for item in checkpoints if item.name == checkpoint_name), None
        )
        if checkpoint_config is None:
            return False

        expected = resume._generate_expected_prompt(
            problem_config,
            checkpoint_config,
            prompt_template,
            environment,
            entry_file,
            is_first_checkpoint=checkpoint_name == checkpoint_names[0],
        )
        expected = _prepend_brief(
            expected, _load_prompt_decisions(checkpoint_dir.parent, checkpoint_name)
        )
        mismatch = not resume._prompts_match(saved_prompt, expected)
        if mismatch:
            resume.logger.info("D1 prompt mismatch detected", checkpoint=checkpoint_name)
        return mismatch

    resume._check_prompt_mismatch = check_prompt_mismatch
    resume._memorycore_d1_patched = True


def _patch_runner() -> None:
    import slop_code.agent_runner.runner as runner
    from slop_code import common

    if getattr(runner, "_memorycore_d1_patched", False):
        return

    original_get_task = runner.get_task_for_checkpoint
    original_run_checkpoint = runner.AgentRunner._run_checkpoint

    def get_task_for_checkpoint(
        checkpoint_name: str,
        spec_text: str,
        template: str,
        entry_file: str,
        environment: Any,
        *,
        is_first_checkpoint: bool,
        output_path: Path,
        agent_type: str | None = None,
        agent_version: str | None = None,
        model_name: str | None = None,
    ) -> str:
        prompt = original_get_task(
            checkpoint_name,
            spec_text,
            template,
            entry_file,
            environment,
            is_first_checkpoint=is_first_checkpoint,
            output_path=output_path,
            agent_type=agent_type,
            agent_version=agent_version,
            model_name=model_name,
        )
        problem_dir = output_path.parent
        decisions = _load_active(problem_dir)
        save_json(_prompt_decisions_path(problem_dir, checkpoint_name), decisions)
        prompt = _prepend_brief(prompt, decisions)
        (output_path / common.PROMPT_FILENAME).write_text(prompt)
        return prompt

    def run_checkpoint(
        self: Any,
        checkpoint: Any,
        checkpoint_save_dir: Path,
        is_first_checkpoint: bool,
    ) -> Any:
        summary = original_run_checkpoint(
            self,
            checkpoint,
            checkpoint_save_dir,
            is_first_checkpoint,
        )
        if getattr(summary, "passed_policy", False):
            problem_dir = checkpoint_save_dir.parent
            spec_text = self.run_spec.problem.get_checkpoint_spec(checkpoint.name)
            new_decisions = extract_decisions_from_spec(
                spec_text,
                checkpoint_name=checkpoint.name,
                max_decisions=_max_decisions_per_checkpoint(),
            )
            active = merge_decisions(_load_active(problem_dir), new_decisions)
            save_json(_checkpoint_decisions_path(problem_dir, checkpoint.name), new_decisions)
            save_json(_active_path(problem_dir), active)
        return summary

    runner.get_task_for_checkpoint = get_task_for_checkpoint
    runner.AgentRunner._run_checkpoint = run_checkpoint
    runner._memorycore_d1_patched = True


def apply_rootless_workspace() -> None:
    import slop_code.execution.docker_runtime.streaming as streaming
    import slop_code.execution.workspace as workspace

    if getattr(workspace, "_memorycore_rootless_patched", False) and getattr(
        streaming, "_memorycore_rootless_patched", False
    ):
        return

    def chmod_or(path: Path, mode_bits: int) -> None:
        path.chmod((path.stat().st_mode & 0o7777) | mode_bits)

    def make_agent_writable(path: Path) -> None:
        for current_root, dirs, files in os.walk(path):
            root_path = Path(current_root)
            if not root_path.is_symlink():
                chmod_or(root_path, 0o777)
            for name in dirs:
                dir_path = root_path / name
                if not dir_path.is_symlink():
                    chmod_or(dir_path, 0o777)
            for name in files:
                file_path = root_path / name
                if not file_path.is_symlink():
                    chmod_or(file_path, 0o666)

    if not getattr(workspace, "_memorycore_rootless_patched", False):
        original_prepare = workspace.Workspace.prepare

        def prepare(self: Any) -> None:
            original_prepare(self)
            make_agent_writable(self.working_dir)

        workspace.Workspace.prepare = prepare
        workspace._memorycore_rootless_patched = True

    if not getattr(streaming, "_memorycore_rootless_patched", False):
        original_cleanup = streaming.DockerStreamingRuntime.cleanup

        def cleanup(self: Any) -> None:
            container = getattr(self, "_container", None)
            if container is not None:
                with contextlib.suppress(Exception):
                    container.reload()
                    state = container.attrs.get("State", {})
                    if state.get("Status") == "running":
                        container.exec_run(
                            "chmod -R a+rwX /workspace || true",
                            user="0:0",
                        )
            original_cleanup(self)

        streaming.DockerStreamingRuntime.cleanup = cleanup
        streaming._memorycore_rootless_patched = True


def apply_decision_layer() -> None:
    _patch_resume_prompt_validation()
    _patch_runner()
