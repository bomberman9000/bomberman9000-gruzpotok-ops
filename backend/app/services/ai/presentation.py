"""Обратная совместимость: presentation V2 в `app.services.presentation.core`."""

from app.services.presentation.core import attach_presentation, build_presentation

__all__ = ["attach_presentation", "build_presentation"]
