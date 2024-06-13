import asyncio
from bleak import BleakClient, BleakScanner

# Replace with the MAC address of your Hexoskin device
hexoskin_address = "00:A0:50:3C:68:76"

# UUIDs for various services and characteristics
HEART_RATE_MEASUREMENT_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
RESPIRATION_SERVICE_UUID = "3b55c581-bc19-48f0-bd8c-b522796f8e24"
RESPIRATION_RATE_MEASUREMENT_CHARACTERISTIC_UUID = "9bc730c3-8cc0-4d87-85bc-573d6304403c"
CLIENT_CHARACTERISTIC_CONFIG_UUID = "00002902-0000-1000-8000-00805f9b34fb"
ACCELEROMETER_SERVICE_UUID = "bdc750c7-2649-4fa8-abe8-fbf25038cda3"
ACCELEROMETER_MEASUREMENT_CHARACTERISTIC_UUID = "75246a26-237a-4863-aca6-09b639344f43"

async def scan_and_list_services():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Found device: {device.name} [{device.address}]")
        if device.address == hexoskin_address:
            print(f"Hexoskin device found: {device.name} [{device.address}]")
            try:
                async with BleakClient(device.address) as client:
                    services = await client.get_services()
                    print(f"Services for device {device.address}:")
                    for service in services:
                        print(f"  [Service] {service.uuid}: {service.description}")
                        for char in service.characteristics:
                            print(f"    [Characteristic] {char.uuid}: {char.description}")
                            for descriptor in char.descriptors:
                                print(f"      [Descriptor] {descriptor.uuid}: {descriptor.description}")
            except Exception as e:
                print(f"Failed to connect to device {device.address}: {e}")
            return

async def connect_and_stream(address):
    async with BleakClient(address) as client:
        print(f"Connected to {address}")
        
        # Read data from Heart Rate Measurement characteristic
        await read_characteristic(client, HEART_RATE_MEASUREMENT_CHARACTERISTIC_UUID, "Heart Rate")
        
        # Read data from Respiration Rate Measurement characteristic
        await read_characteristic(client, RESPIRATION_RATE_MEASUREMENT_CHARACTERISTIC_UUID, "Respiration Rate")
        
        # Read data from Accelerometer Measurement characteristic
        await read_characteristic(client, ACCELEROMETER_MEASUREMENT_CHARACTERISTIC_UUID, "Accelerometer")

async def read_characteristic(client, characteristic_uuid, characteristic_name):
    try:
        while True:
            data = await client.read_gatt_char(characteristic_uuid)
            print(f"{characteristic_name} Data: {data}")
            await asyncio.sleep(1)  # Adjust the polling interval as needed
    except Exception as e:
        print(f"Error reading from {characteristic_name} characteristic: {e}")

def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(scan_and_list_services())

    address = hexoskin_address
    loop.run_until_complete(connect_and_stream(address))

if __name__ == "__main__":
    main()
