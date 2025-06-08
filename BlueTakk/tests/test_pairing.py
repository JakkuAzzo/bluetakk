import asyncio
from peripheral_simulator import VirtualPeripheral, simulate_exchange


def test_pair_and_exchange():
    a = VirtualPeripheral("A")
    b = VirtualPeripheral("B")
    msgs_a = ["hi", "there"]
    msgs_b = ["hello"]
    out_a, out_b = asyncio.run(simulate_exchange(a, b, msgs_a, msgs_b, interval=0))
    assert out_a == ["B:hello"]
    assert out_b == ["A:hi", "A:there"]
