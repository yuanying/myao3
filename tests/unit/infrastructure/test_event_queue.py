"""Tests for EventQueue."""

import asyncio

from myao3.domain.entities.event import PingEvent
from myao3.infrastructure.event_queue import EventQueue


class TestEventQueue:
    """Tests for EventQueue class."""

    async def test_basic_enqueue_dequeue(self) -> None:
        """TC-05-001: Basic enqueue and dequeue operation."""
        queue = EventQueue()
        event = PingEvent()

        await queue.enqueue(event)
        result = await queue.dequeue()

        assert result.id == event.id

    async def test_duplicate_event_skipped(self) -> None:
        """TC-05-002: Duplicate events with same identity_key are skipped."""
        queue = EventQueue()
        event1 = PingEvent()
        event2 = PingEvent()

        await queue.enqueue(event1)
        await queue.enqueue(event2)

        # First dequeue returns the newer event (event2)
        result = await queue.dequeue()
        assert result.id == event2.id

        # Second dequeue blocks (no more events available)
        try:
            async with asyncio.timeout(0.1):
                await queue.dequeue()
                assert False, "Should have timed out"
        except TimeoutError:
            pass  # Expected

    async def test_delayed_enqueue(self) -> None:
        """TC-05-003: Event is enqueued after specified delay."""
        queue = EventQueue()
        event = PingEvent()

        await queue.enqueue(event, delay=0.1)

        # Immediate dequeue should timeout
        try:
            async with asyncio.timeout(0.05):
                await queue.dequeue()
                assert False, "Should have timed out"
        except TimeoutError:
            pass  # Expected

        # After waiting, event should be available
        await asyncio.sleep(0.15)
        async with asyncio.timeout(0.1):
            result = await queue.dequeue()
            assert result.id == event.id

    async def test_delayed_enqueue_cancel(self) -> None:
        """TC-05-004: Delayed enqueue is cancelled when new event is enqueued."""
        queue = EventQueue()
        event1 = PingEvent()
        event2 = PingEvent()

        # Enqueue event1 with 1 second delay
        await queue.enqueue(event1, delay=1.0)

        # After 0.1 seconds, enqueue event2 without delay
        await asyncio.sleep(0.1)
        await queue.enqueue(event2, delay=0)

        # Should get event2 immediately
        async with asyncio.timeout(0.1):
            result = await queue.dequeue()
            assert result.id == event2.id

        # After the original delay for event1 has fully passed, no further events
        # should be enqueued, since its delayed enqueue was cancelled.
        await asyncio.sleep(1.1)
        try:
            async with asyncio.timeout(0.1):
                await queue.dequeue()
                assert False, "Should have timed out after cancelled delayed event"
        except TimeoutError:
            pass  # Expected

    async def test_mark_done(self) -> None:
        """TC-05-005: mark_done removes event from processing."""
        queue = EventQueue()
        event = PingEvent()

        await queue.enqueue(event)
        result = await queue.dequeue()

        # After dequeue, event is in processing
        assert queue.processing_count == 1

        # After mark_done, event is removed from processing
        queue.mark_done(result)
        assert queue.processing_count == 0

    async def test_new_event_during_processing(self) -> None:
        """TC-05-006: New event with same key can be processed during processing."""
        queue = EventQueue()
        event1 = PingEvent()
        event2 = PingEvent()

        # Enqueue and dequeue event1 (without mark_done)
        await queue.enqueue(event1)
        result1 = await queue.dequeue()
        assert result1.id == event1.id

        # Enqueue event2 while event1 is still processing
        await queue.enqueue(event2)

        # Should be able to dequeue event2
        async with asyncio.timeout(0.1):
            result2 = await queue.dequeue()
            assert result2.id == event2.id

        # Both are in processing
        assert queue.processing_count == 2

        # Mark both as done
        queue.mark_done(result1)
        queue.mark_done(result2)
        assert queue.processing_count == 0

    async def test_pending_count(self) -> None:
        """TC-05-007: pending_count tracks pending events correctly."""
        queue = EventQueue()
        event = PingEvent()

        # Initial state
        assert queue.pending_count == 0

        # After enqueue
        await queue.enqueue(event)
        assert queue.pending_count == 1

        # After dequeue
        await queue.dequeue()
        assert queue.pending_count == 0

    async def test_multiple_identity_keys(self) -> None:
        """TC-05-008: Events with different identity_keys are independent."""
        queue = EventQueue()
        # Create events with different identity_keys
        ping_event = PingEvent()  # identity_key = "ping"

        # Create a custom event with different identity_key
        from myao3.domain.entities.event import Event, EventType

        custom_event = Event(
            type=EventType.PING, source="test"
        )  # identity_key = event.id

        await queue.enqueue(ping_event)
        await queue.enqueue(custom_event)

        # Both events should be retrievable (order is enqueue order)
        result1 = await queue.dequeue()
        result2 = await queue.dequeue()

        assert {result1.id, result2.id} == {ping_event.id, custom_event.id}
