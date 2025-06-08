"""Reusable templates for common MITM actions."""

import asyncio
from mac_mitm import MacMITMProxy


async def mac_notification_mitm(target_address: str) -> None:
    """Forward notifications from the target and attempt to inject one."""
    proxy = MacMITMProxy(target_address)
    await proxy.connect_to_target()

    async def log_notification(sender, data):
        print(f"{sender}: {data}")

    for service in proxy.target_services:
        for char in service.characteristics:
            if "notify" in getattr(char, "properties", []):
                await proxy.client.start_notify(char.uuid, log_notification)

    # Example injection of a dummy notification
    if proxy.target_services:
        first = proxy.target_services[0].characteristics[0]
        await proxy.forward_write(first.uuid, b"template-notify")
    await asyncio.sleep(5)
