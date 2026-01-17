"""EventQueue implementation with deduplication and delayed enqueue support."""

import asyncio

from myao3.domain.entities.event import Event


class EventQueue:
    """In-memory event queue with deduplication and delayed enqueue support.

    Supports:
    - Deduplication based on identity_key
    - Delayed enqueue with cancellation
    - Processing state tracking
    """

    def __init__(self) -> None:
        """Initialize the event queue."""
        self._queue: asyncio.Queue[Event] = asyncio.Queue()
        self._pending: dict[str, Event] = {}
        # Use event.id as key to allow multiple events with same identity_key
        self._processing: dict[str, Event] = {}
        self._delay_tasks: dict[str, asyncio.Task[None]] = {}

    @property
    def pending_count(self) -> int:
        """Return the number of pending events."""
        return len(self._pending)

    @property
    def processing_count(self) -> int:
        """Return the number of events being processed."""
        return len(self._processing)

    async def enqueue(self, event: Event, delay: float = 0) -> None:
        """Add an event to the queue.

        Args:
            event: The event to enqueue.
            delay: Delay in seconds before the event is added to the queue.
                   Defaults to 0 (immediate enqueue).
        """
        key = event.get_identity_key()

        # Cancel existing delayed task for this key
        if key in self._delay_tasks:
            self._delay_tasks[key].cancel()
            try:
                await self._delay_tasks[key]
            except asyncio.CancelledError:
                pass
            # Task may have already been removed by _delayed_enqueue's finally block
            self._delay_tasks.pop(key, None)

        if delay > 0:
            # Create delayed enqueue task
            task = asyncio.create_task(self._delayed_enqueue(event, delay))
            self._delay_tasks[key] = task
        else:
            # Immediate enqueue.
            # Note: If another event with the same key is enqueued between setting
            # _pending[key] and calling _queue.put(), the pending dict will be
            # overwritten but the old event remains in the queue. The dequeue
            # logic handles this by skipping stale events.
            self._pending[key] = event
            await self._queue.put(event)

    async def _delayed_enqueue(self, event: Event, delay: float) -> None:
        """Internal method to enqueue an event after a delay.

        Args:
            event: The event to enqueue.
            delay: Delay in seconds.
        """
        key = event.get_identity_key()
        try:
            await asyncio.sleep(delay)
            self._pending[key] = event
            await self._queue.put(event)
        finally:
            # Clean up the task reference
            if key in self._delay_tasks:
                del self._delay_tasks[key]

    async def dequeue(self) -> Event:
        """Get the next event from the queue.

        Skips stale events (those that have been superseded by newer events
        with the same identity_key).

        Returns:
            The next event to process.
        """
        while True:
            event = await self._queue.get()
            key = event.get_identity_key()

            # Check if this event is still the current pending event for this key
            if key in self._pending and self._pending[key].id == event.id:
                # This is the current event, move to processing
                del self._pending[key]
                self._processing[event.id] = event
                return event
            # Otherwise, this is a stale event; skip it and get the next one

    def mark_done(self, event: Event) -> None:
        """Mark an event as done processing.

        Args:
            event: The event that has been processed.
        """
        if event.id in self._processing:
            del self._processing[event.id]
