"""LGX extension — LangGraph-based agents for Renglo."""

__version__ = "1.0.0"
__all__ = ["get_handler", "list_handlers", "HANDLERS"]


def _get_lgx_onboardings():
    from lgx.handlers.lgx_onboardings import LgxOnboardings

    return LgxOnboardings


HANDLERS = {
    "lgx_onboardings": _get_lgx_onboardings,
}


def get_handler(handler_name: str):
    """Get an instantiated handler by name."""
    if handler_name not in HANDLERS:
        available = ", ".join(HANDLERS.keys())
        raise KeyError(
            f"Handler '{handler_name}' not found. Available handlers: {available}"
        )

    return HANDLERS[handler_name]()


def list_handlers():
    """List all available handler names."""
    return list(HANDLERS.keys())
