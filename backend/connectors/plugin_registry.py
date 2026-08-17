"""
Plugin Registry — optional connector plug-ins controlled by ENABLE_* env vars.

Rules
-----
* Does NOT modify any existing connector.
* Does NOT touch the crawler pipeline or scheduler.
* Returns a flat list of connector *classes* that the existing __init__.py
  appends to ALL_CONNECTORS.  The worker instantiates them exactly as before.
* If all flags are False, returns an empty list → existing connectors run as-is.
"""
from __future__ import annotations

import structlog
from core.config import settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Mapping: (enable_flag_attr, connector_module, connector_class_name)
# ---------------------------------------------------------------------------
_PLUGIN_SPECS: list[tuple[str, str, str]] = [
    ("ENABLE_APIFY",       "connectors.apify_connector",      "ApifyConnector"),
    ("ENABLE_FIRECRAWL",   "connectors.firecrawl_connector",  "FirecrawlConnector"),
    ("ENABLE_CRAWL4AI",    "connectors.crawl4ai_connector",   "Crawl4AIConnector"),
    ("ENABLE_PLAYWRIGHT",  "connectors.playwright_connector", "PlaywrightConnector"),
    ("ENABLE_BROWSERBASE", "connectors.browserbase_connector","BrowserbaseConnector"),
    ("ENABLE_BRIGHTDATA",  "connectors.brightdata_connector", "BrightDataConnector"),
    ("ENABLE_SERPAPI",     "connectors.serpapi_connector",    "SerpAPIConnector"),
    ("ENABLE_RAPIDAPI",    "connectors.rapidapi_connector",   "RapidAPIConnector"),
]


def get_enabled_plugin_classes() -> list[type]:
    """
    Return connector *classes* for every plugin whose ENABLE_* flag is True.
    Imports are lazy so disabled connectors never load their optional deps.
    """
    import importlib

    enabled: list[type] = []

    for flag_attr, module_path, class_name in _PLUGIN_SPECS:
        is_enabled: bool = getattr(settings, flag_attr, False)
        if not is_enabled:
            log.debug("plugin.disabled", connector=class_name)
            continue

        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            enabled.append(cls)
            log.info("plugin.enabled", connector=class_name)
        except Exception as exc:
            # Never crash the whole application for a single plugin failure.
            log.error(
                "plugin.load_failed",
                connector=class_name,
                error=str(exc),
            )

    log.info("plugins.loaded", total=len(enabled))
    return enabled
