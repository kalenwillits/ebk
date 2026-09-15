"""Build-time Tailwind CSS compilation.

Wraps the `pytailwindcss` package, which downloads and runs Tailwind's
standalone CLI binary -- no Node.js/npm required, so this fits ebk's
single-binary PyInstaller distribution model.

Tailwind v4's CLI has built-in automatic content detection: pointed at a
directory via --cwd, it scans text files for literal utility-class strings
with no content-glob configuration needed. That means classes written
directly in markdown, or embedded in config.yaml's `tw:` alias values, are
both picked up with no extra wiring on ebk's part.
"""

import os
import tempfile
from pathlib import Path

from ebk.core.styles import CssLayer


class TailwindUnavailableError(Exception):
    """Raised when Tailwind CSS compilation can't proceed: pytailwindcss
    isn't installed, the tailwindcss binary can't be downloaded (e.g.
    offline on first use), or the tailwindcss binary fails to run.

    Callers should catch this and continue the build without the Tailwind
    layer, rather than fail the whole build.
    """


def tailwind_enabled(config):
    """Whether config.yaml opts into build-time Tailwind compilation.

    Off by default: absent, or an explicit `tailwind: { enabled: false }`,
    means no Tailwind step runs at all -- no subprocess, no network.
    """
    if not isinstance(config, dict):
        return False
    tailwind_config = config.get('tailwind') or {}
    return bool(tailwind_config.get('enabled'))


def _bin_path(version):
    """A stable, per-user cache location for the downloaded tailwindcss
    binary. Kept outside the pytailwindcss package's own install directory
    (its default) so the download survives across runs of a frozen
    PyInstaller ebk binary, whose bundled site-packages location isn't a
    stable place to cache a download between invocations.
    """
    binary_name = 'tailwindcss.exe' if os.name == 'nt' else 'tailwindcss'
    return Path.home() / '.cache' / 'ebk' / 'tailwindcss' / version / binary_name


def compile_tailwind_css(project_root, config, output_name='tailwind.css'):
    """Compile a project's Tailwind utility classes into a CssLayer.

    Returns None immediately (no subprocess, no network) if config.yaml's
    tailwind.enabled is not truthy.

    Raises TailwindUnavailableError if pytailwindcss isn't installed, or if
    compilation fails (including a first-run binary download failure, e.g.
    while offline) -- callers should catch this and degrade gracefully.
    """
    if not tailwind_enabled(config):
        return None

    try:
        import pytailwindcss
    except ImportError as err:
        raise TailwindUnavailableError(
            "Tailwind support requires the 'pytailwindcss' package. "
            "Install it with: pip install pytailwindcss"
        ) from err

    tailwind_config = config.get('tailwind') or {}
    version = tailwind_config.get('version', 'latest')
    bin_path = _bin_path(version)

    with tempfile.TemporaryDirectory(prefix='ebk-tailwind-') as tmp_dir:
        entry_css = os.path.join(tmp_dir, 'input.css')
        output_css = os.path.join(tmp_dir, 'output.css')
        with open(entry_css, 'w', encoding='utf-8') as f:
            f.write('@import "tailwindcss";\n')

        try:
            pytailwindcss.run(
                ['-i', entry_css, '-o', output_css, '--cwd', project_root,
                 '--minify', '--silent'],
                bin_path=bin_path,
                auto_install=True,
                version=version,
            )
        except Exception as err:
            raise TailwindUnavailableError(
                f"Tailwind CSS compilation failed (are you offline? the "
                f"Tailwind CLI binary may need to download on first use): {err}"
            ) from err

        if not os.path.exists(output_css):
            raise TailwindUnavailableError(
                "Tailwind CSS compilation produced no output"
            )

        with open(output_css, 'r', encoding='utf-8') as f:
            compiled_css = f.read()

    return CssLayer(name=output_name, text=compiled_css, source='tailwind')


def try_compile_tailwind_css(project_root, config, output_name='tailwind.css'):
    """Like compile_tailwind_css, but never raises: on failure, prints a
    warning and returns None so the build continues without the Tailwind
    layer (default.css and project CSS still apply normally).
    """
    try:
        return compile_tailwind_css(project_root, config, output_name=output_name)
    except TailwindUnavailableError as err:
        print(f"  Warning: Tailwind CSS compilation skipped: {err}")
        return None
