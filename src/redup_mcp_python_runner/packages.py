"""Allowlisted preinstalled packages (no runtime install)."""

from __future__ import annotations

from pathlib import Path

# Fallback if packages.txt is missing from the install layout.
_DEFAULT_PACKAGES = (
    "numpy",
    "pandas",
    "matplotlib",
    "scipy",
    "scikit-learn",
    "pillow",
    "sympy",
    "pyyaml",
    "polars",
    "pydantic",
    "rich",
)


def packages_file_candidates() -> list[Path]:
    """Likely locations for packages.txt (install / repo / Docker)."""
    here = Path(__file__).resolve()
    return [
        Path("/config/packages.txt"),
        Path("/opt/code-tools-env/packages.txt"),
        here.parents[2] / "packages.txt",  # repo root when editable
        here.parent / "packages.txt",
    ]


def load_package_list(packages_file: Path | str | None = None) -> list[str]:
    """Load package names from a file, else built-in defaults."""
    paths: list[Path] = []
    if packages_file:
        paths.append(Path(packages_file))
    paths.extend(packages_file_candidates())

    for path in paths:
        try:
            if path.is_file():
                names: list[str] = []
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Allow "name==1.2" pins in the file; expose bare name to agents.
                    name = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()
                    if name:
                        names.append(name)
                if names:
                    return names
        except OSError:
            continue
    return list(_DEFAULT_PACKAGES)
