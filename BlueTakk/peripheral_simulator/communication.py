"""In-memory simulation of two BLE peripherals communicating.

This module does not use real Bluetooth hardware. It exposes a simple model
where two :class:`VirtualPeripheral` instances can be paired and exchange
messages at a configurable interval. It is primarily intended for unit tests
and demonstrations when physical adapters are unavailable.
"""

from __future__ import annotations

import asyncio
from typing import List, Tuple


class VirtualPeripheral:
    """A very small virtual peripheral object."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.peer: VirtualPeripheral | None = None
        self.inbox: asyncio.Queue[str] = asyncio.Queue()
        self.last_pair_request: dict | None = None

    def pair(self, other: "VirtualPeripheral", request_modifier=None) -> None:
        """Pair this peripheral with another.

        A ``request_modifier`` callable can be supplied to modify the
        connection request. It receives a dictionary with ``name`` and
        ``address`` keys and should return a dictionary that will be stored on
        the peer as ``last_pair_request``. This is a light-weight stand in for
        the reverse pairing behaviour in real devices.
        """
        request = {"name": other.name, "address": getattr(other, "address", "")}
        if request_modifier:
            request = request_modifier(request) or request
        self.peer = other
        other.peer = self
        self.last_pair_request = request

    async def send(self, data: str) -> None:
        """Send a text payload to the paired peripheral."""
        if not self.peer:
            raise RuntimeError("Peripheral is not paired")
        await self.peer.inbox.put(f"{self.name}:{data}")

    async def receive_all(self) -> List[str]:
        """Return all queued messages."""
        items: List[str] = []
        while not self.inbox.empty():
            items.append(await self.inbox.get())
        return items


async def simulate_exchange(
    a: VirtualPeripheral,
    b: VirtualPeripheral,
    messages_a: List[str],
    messages_b: List[str],
    interval: float = 1.0,
) -> Tuple[List[str], List[str]]:
    """Simulate a bidirectional exchange.

    ``messages_a`` and ``messages_b`` are lists of text messages that will be
    sent from ``a`` and ``b`` respectively. The function waits ``interval``
    seconds between each round and returns all messages received by both
    peripherals at the end of the exchange.
    """

    a.pair(b)
    max_len = max(len(messages_a), len(messages_b))

    for i in range(max_len):
        if i < len(messages_a):
            await a.send(messages_a[i])
        if i < len(messages_b):
            await b.send(messages_b[i])
        await asyncio.sleep(interval)

    return await a.receive_all(), await b.receive_all()
