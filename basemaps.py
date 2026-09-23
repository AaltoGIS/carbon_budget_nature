"""Keyed CARTO basemap providers for contextily.

CARTO watermarks anonymous tiles ("API KEY REQUIRED"). Set the key in the
environment (never in the repository), e.g. in ~/.bashrc:

    export CARTO_KEY=...

or put the bare key in ~/.config/carto/key (chmod 600) for Jupyter kernels
that do not source ~/.bashrc.

Free key: https://carto.com/basemaps/apikey  (5M tiles/month, non-commercial,
OSM + CARTO attribution must stay visible).
"""
import os
from pathlib import Path

import contextily as ctx

_URL = "https://basemaps.cartocdn.com/rastertiles/{variant}/{z}/{x}/{y}{r}.png?key={key}"
_KEY_FILE = Path.home() / ".config" / "carto" / "key"


def _load_key():
    key = os.environ.get("CARTO_KEY")
    if not key and _KEY_FILE.exists():          # Jupyter kernels may not see ~/.bashrc
        key = _KEY_FILE.read_text()
    return "".join(key.split()) or None      # drop stray tabs/newlines from copy-paste


_KEY = _load_key()

# Fetch each tile once; cache on disk instead of re-downloading every run.
ctx.set_cache_dir(str(Path.home() / ".cache" / "contextily"))


def _keyed(provider):
    if not _KEY:
        # Fall back to the anonymous (watermarked) provider rather than failing.
        return provider
    # Voyager's variant is "rastertiles/voyager"; the keyed URL already has that prefix.
    variant = provider["variant"].removeprefix("rastertiles/")
    return provider(url=_URL, key=_KEY, variant=variant)


POSITRON          = _keyed(ctx.providers.CartoDB.Positron)
POSITRON_NOLABELS = _keyed(ctx.providers.CartoDB.PositronNoLabels)
DARK_NOLABELS     = _keyed(ctx.providers.CartoDB.DarkMatterNoLabels)
VOYAGER           = _keyed(ctx.providers.CartoDB.Voyager)

if not _KEY:
    import warnings
    warnings.warn("CARTO_KEY not set - basemaps will carry the 'API KEY REQUIRED' watermark.")
