"""
Connector registry — Indian procurement portals & private sector RFPs.
International connectors (TED EU, Contracts Finder, SAM.gov, World Bank) are excluded.
"""
import structlog
from connectors.gem import GeMConnector
from connectors.cppp import CPPPConnector
from connectors.indian_railways import IndianRailwaysConnector
from connectors.private_sector import PrivateSectorConnector
from connectors.psu import build_psu_connectors
from connectors.state_eprocurement import build_state_connectors
from connectors.municipal import build_municipal_connectors
from connectors.plugin_registry import get_enabled_plugin_classes

# Optional plug-ins loaded on-demand via plugin_registry
ApifyConnector = None
FirecrawlConnector = None
Crawl4AIConnector = None
PlaywrightConnector = None
BrowserbaseConnector = None
BrightDataConnector = None
SerpAPIConnector = None
TavilyConnector = None
ExaSearchConnector = None
RapidAPIConnector = None

log = structlog.get_logger()

# Core Indian portals & Private sector — always enabled
_CORE_CONNECTORS = [
    GeMConnector,
    CPPPConnector,
    PrivateSectorConnector,
]

# Optional plug-ins (controlled by ENABLE_* env flags)
_PLUGIN_CONNECTORS = []

ALL_CONNECTORS = _CORE_CONNECTORS + _PLUGIN_CONNECTORS

# Factory-built instances — PSU / State / Municipal
_PSU_CONNECTORS     = []
_STATE_CONNECTORS   = build_state_connectors()
_MUNICIPAL_CONNECTORS = []

# Flat list used by crawl_worker
ALL_CONNECTOR_INSTANCES = (
    [cls() for cls in ALL_CONNECTORS]
    + _STATE_CONNECTORS
)

# Log enabled connectors at startup
log.info("connectors.loaded", total=len(ALL_CONNECTOR_INSTANCES),
         sources=[c.source_id for c in ALL_CONNECTOR_INSTANCES])

__all__ = [
    "ALL_CONNECTORS", "ALL_CONNECTOR_INSTANCES",
    "GeMConnector", "CPPPConnector", "IndianRailwaysConnector", "PrivateSectorConnector",
    "ApifyConnector", "FirecrawlConnector", "Crawl4AIConnector",
    "PlaywrightConnector", "BrowserbaseConnector", "BrightDataConnector",
    "SerpAPIConnector", "TavilyConnector", "ExaSearchConnector", "RapidAPIConnector",
    "build_psu_connectors", "build_state_connectors", "build_municipal_connectors",
    "get_enabled_plugin_classes",
]

