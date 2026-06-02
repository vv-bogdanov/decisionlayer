from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf

from memorycore.experiments.run_experiment import run_experiment


@hydra.main(version_base=None, config_path="../../configs/hydra", config_name="experiment")
def main(config: DictConfig) -> None:
    plain_config = OmegaConf.to_container(config, resolve=False)
    if not isinstance(plain_config, dict):
        raise TypeError("Hydra experiment config must be a mapping")
    experiment_config = with_hydra_output_dir(cast(dict[str, Any], dict(plain_config)))
    result = run_experiment(experiment_config)
    print(json.dumps(result["metrics"], ensure_ascii=False, indent=2))


def with_hydra_output_dir(config: dict[str, Any]) -> dict[str, Any]:
    if not HydraConfig.initialized():
        return config
    job = HydraConfig.get().job
    job_num = getattr(job, "num", None)
    if job_num is None:
        return config
    output_dir = str(config.get("output_dir") or "reports/hydra_multirun")
    placeholder = "${hydra.job.num}"
    escaped_placeholder = "$\\{hydra.job.num\\}"
    if placeholder in output_dir or escaped_placeholder in output_dir:
        config["output_dir"] = output_dir.replace(placeholder, str(job_num)).replace(escaped_placeholder, str(job_num))
    else:
        config["output_dir"] = str(Path(output_dir) / str(job_num))
    return config


if __name__ == "__main__":
    main()
