# src/services/event_emitter.py

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

# In-process event bus.
# Multiple handlers can subscribe to the same event.
class EventEmitter:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    # Register a handler for an event.
    def subscribe(self, event_name: str, handler: Callable) -> None:
        self._handlers[event_name].append(handler)

    # Publish an event to all subscribers.
    def emit(self, event_name: str, **payload) -> None:
        for handler in self._handlers.get(event_name, []):
            handler(**payload)


event_emitter = EventEmitter()