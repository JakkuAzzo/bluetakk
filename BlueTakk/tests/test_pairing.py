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


def test_pair_request_modifier():
    captured = {}

    def modifier(req):
        captured.update(req)
        req["address"] = "XX"
        return req

    a = VirtualPeripheral("A")
    b = VirtualPeripheral("B")
    a.pair(b, request_modifier=modifier)
    assert a.last_pair_request["address"] == "XX"
    assert captured["name"] == "B"
