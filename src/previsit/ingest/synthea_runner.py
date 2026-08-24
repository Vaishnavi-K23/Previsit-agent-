"""Downloads and runs Synthea to generate synthetic FHIR R4 patient bundles.

Synthea is a Java application distributed as a self-contained jar
(`synthea-with-dependencies.jar`) via GitHub releases. This module downloads
that jar once (cached locally, never committed) and invokes it as a
subprocess — no clinical logic lives here, this is purely an invocation
wrapper.

If a `java` binary isn't on this host's PATH but WSL is (the case on a
Windows dev machine that installed a JRE inside WSL2 rather than natively),
calls are transparently routed through `wsl.exe` instead of failing.
"""

import platform
import shutil
import subprocess
from pathlib import Path

import httpx

from previsit.config import settings

RELEASE_API_URL = "https://api.github.com/repos/synthetichealth/synthea/releases/latest"
JAR_ASSET_NAME = "synthea-with-dependencies.jar"
CACHE_DIR = Path(".synthea_cache")


def _jar_path() -> Path:
    return CACHE_DIR / JAR_ASSET_NAME


def ensure_jar() -> Path:
    """Downloads the Synthea jar if not already cached. Returns its local path."""
    jar_path = _jar_path()
    if jar_path.exists():
        return jar_path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(RELEASE_API_URL, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    release = resp.json()
    asset = next(a for a in release["assets"] if a["name"] == JAR_ASSET_NAME)

    print(f"Downloading Synthea ({release['tag_name']}) from {asset['browser_download_url']}")
    with httpx.stream(
        "GET", asset["browser_download_url"], timeout=120, follow_redirects=True
    ) as stream:
        stream.raise_for_status()
        tmp_path = jar_path.with_suffix(".jar.part")
        with open(tmp_path, "wb") as f:
            for chunk in stream.iter_bytes():
                f.write(chunk)
        tmp_path.rename(jar_path)

    return jar_path


def _win_to_wsl_path(path: Path) -> str:
    """Converts an absolute Windows path to its /mnt/<drive>/... WSL2 equivalent."""
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    rest = str(resolved)[len(resolved.drive) + 1 :].replace("\\", "/")
    return f"/mnt/{drive}/{rest}"


def _java_available_natively() -> bool:
    return shutil.which("java") is not None


def _build_command(jar_path: Path, output_dir: Path, population: int, state: str) -> list[str]:
    # Synthea does NOT read `-Dexporter.baseDirectory=...` JVM system properties for
    # config overrides (verified empirically - it's silently ignored, output falls back
    # to the jar's bundled default of ./output/). The actual mechanism, per Synthea's
    # own README, is a `--config*=value` *program* argument, e.g.
    # `run_synthea --exporter.baseDirectory="./output_tx/" Texas`.
    exporter_dir_arg = "--exporter.baseDirectory={output_dir}/"

    if _java_available_natively():
        return [
            "java",
            "-jar",
            str(jar_path.resolve()),
            "-p",
            str(population),
            exporter_dir_arg.format(output_dir=str(output_dir.resolve())),
            state,
        ]

    if platform.system() == "Windows":
        # No native java; fall back to the JRE installed inside WSL2.
        # `-e`/`--exec` is required here, not `--`: `wsl.exe -- <cmd>` re-joins the
        # trailing args into a string and reparses it through the default Linux shell,
        # which re-splits on any space in a path (e.g. "Documents/python projects/...").
        # `-e` execs the argv directly, preserving argument boundaries exactly.
        wsl_jar = _win_to_wsl_path(jar_path)
        wsl_output = _win_to_wsl_path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)  # must pre-exist on the Windows side too
        return [
            "wsl.exe",
            "-d",
            "Ubuntu",
            "-e",
            "java",
            "-jar",
            wsl_jar,
            "-p",
            str(population),
            exporter_dir_arg.format(output_dir=wsl_output),
            state,
        ]

    raise RuntimeError(
        "No `java` binary found on PATH, and this isn't Windows so there's no WSL fallback. "
        "Install a JRE (11+) and re-run."
    )


def run(population: int | None = None, state: str | None = None) -> Path:
    """Runs Synthea, generating `population` patients in `state`.

    Returns the output directory. Synthea writes FHIR bundles under
    `<output_dir>/fhir/`.
    """
    population = population or settings.synthea_population
    state = state or settings.synthea_state
    output_dir = Path(settings.synthea_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jar_path = ensure_jar()
    cmd = _build_command(jar_path, output_dir, population, state)

    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

    return output_dir


if __name__ == "__main__":
    run()
