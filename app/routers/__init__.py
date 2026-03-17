from .pages        import router as pages_router
from .calls        import router as calls_router
from .leads        import router as leads_router
from .campaigns    import router as campaigns_router
from .config_router import router as config_router
from .webhooks     import router as webhooks_router
from .ivr          import router as ivr_router

__all__ = [
    "pages_router", "calls_router", "leads_router",
    "campaigns_router", "config_router", "webhooks_router", "ivr_router",
]
