"""batch.py — Batch processing of GPR data using pipelines.

exports: process_batch(recipe: str|dict, filepaths: list[str], max_workers: int, progress_callback: callable) -> dict
used_by: dig/cli.py -> main
rules:
  - Must use ProcessPoolExecutor for parallelization.
  - Processing recipes defined in dict, supporting JSON/YAML loading.
"""

import concurrent.futures
import importlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

try:
    import yaml
except ImportError:
    yaml = None

from dig.parsers.dt1 import DT1File
from dig.parsers.dzt import DZTFile
from dig.processing.pipeline import ProcessingPipeline


def load_recipe(recipe: Union[str, Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Load a processing recipe from a file path or dict/list."""
    if isinstance(recipe, dict):
        # Allow wrapper dicts like {"steps": [...]}
        return recipe.get("steps", [recipe]) if "steps" in recipe else [recipe]
    if isinstance(recipe, list):
        return recipe

    path = str(recipe)
    if path.endswith(".json"):
        with open(path, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("steps", [data])
            return data
    elif path.endswith((".yaml", ".yml")):
        if yaml is None:
            raise ImportError("PyYAML is not installed. Cannot load YAML recipes.")
        with open(path, "r") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                return data.get("steps", [data])
            return data
    else:
        raise ValueError(f"Unsupported recipe format: {path}")


def resolve_function(step_name: str) -> Callable:
    """Resolve a function name to an actual Python function in dig.processing."""
    modules = [
        "background",
        "bandpass",
        "detection",
        "dewow",
        "gain",
        "magnetometry",
        "migration",
        "time_zero",
        "topography",
    ]
    for mod_name in modules:
        try:
            mod = importlib.import_module(f"dig.processing.{mod_name}")
            if hasattr(mod, step_name):
                return getattr(mod, step_name)
        except ImportError:
            pass
    raise ValueError(f"Unknown processing step: {step_name}")


def _process_single_file(filepath: str, recipe_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Worker function to process a single file.
    Must be top-level for ProcessPoolExecutor pickling.
    """
    path = Path(filepath)
    if not path.exists():
        return {"file": filepath, "status": "error", "error": "File not found"}

    try:
        ext = path.suffix.lower()
        parser: Union[DZTFile, DT1File]
        if ext == ".dzt":
            parser = DZTFile(filepath)
            data = parser.traces
            metadata = getattr(parser, "metadata", {})
        elif ext == ".dt1":
            parser = DT1File(filepath)
            data = parser.traces
            metadata = getattr(parser, "metadata", {})
        else:
            return {"file": filepath, "status": "error", "error": f"Unsupported extension: {ext}"}

        pipe = ProcessingPipeline(data, survey_metadata=metadata)

        for step in recipe_steps:
            func_name = step.get("name") or step.get("step")
            if not func_name:
                continue

            kwargs = step.get("params", {})
            func = resolve_function(func_name)

            pipe = pipe.process(func, **kwargs)

        return {
            "file": filepath,
            "status": "success",
            "num_steps": pipe.num_steps,
            "history": pipe.export_history(),
            "final_shape": list(pipe.data.shape) if pipe.data is not None else None,
        }
    except Exception as e:
        return {"file": filepath, "status": "error", "error": str(e)}


def process_batch(
    recipe: Union[str, Dict[str, Any], List[Dict[str, Any]]],
    filepaths: List[str],
    max_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> List[Dict[str, Any]]:
    """Process multiple files using a recipe in parallel.

    Args:
        recipe: Path to JSON/YAML recipe, or dict/list of steps.
        filepaths: List of file paths to process.
        max_workers: Max processes for concurrent execution.
        progress_callback: Callback invoked as callback(completed, total)

    Returns:
        List of dicts with processing results per file.
    """
    try:
        steps = load_recipe(recipe)
    except Exception as e:
        raise ValueError(f"Failed to load recipe: {e}")

    results = []
    total = len(filepaths)
    completed = 0

    if progress_callback:
        progress_callback(completed, total)

    with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(_process_single_file, fp, steps): fp for fp in filepaths}

        for future in concurrent.futures.as_completed(future_to_file):
            fp = future_to_file[future]
            try:
                res = future.result()
            except Exception as exc:
                res = {"file": fp, "status": "error", "error": str(exc)}

            results.append(res)
            completed += 1
            if progress_callback:
                progress_callback(completed, total)

    return results
