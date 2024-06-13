import asyncio
from bleak import BleakClient, BleakScanner

async def scan_and_list_services():
    devices = await BleakScanner.discover()
    for device in devices:
        print(device)
        async with BleakClient(device.address) as client:
            services = await client.get_services()
            for service in services:
                print(f"[Service] {service.uuid}: {service.description}")
                for char in service.characteristics:
                    print(f"  [Characteristic] {char.uuid}: {char.description}")

loop = asyncio.get_event_loop()
loop.run_until_complete(scan_and_list_services())