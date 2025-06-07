import deepBle_discovery_tool as deep


def test_format_uuid_forms_short():
    uuid = "0000180a-0000-1000-8000-00805f9b34fb"
    assert deep.format_uuid_forms(uuid) == "0x180A / 0000180a-0000-1000-8000-00805f9b34fb"


def test_format_uuid_forms_full():
    uuid = "12345678-1234-5678-1234-56789abcdef0"
    assert deep.format_uuid_forms(uuid) == uuid

