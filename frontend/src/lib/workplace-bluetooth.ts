const SERVICE_UUID = 'b15a0a00-571d-4a73-95de-6d660c00b001';
const REQUEST_UUID = 'b15a0a01-571d-4a73-95de-6d660c00b001';

type Characteristic = {
  properties?: { writeWithoutResponse?: boolean };
  writeValueWithResponse(value: BufferSource): Promise<void>;
  writeValueWithoutResponse?: (value: BufferSource) => Promise<void>;
};
type GattServer = { getPrimaryService(uuid: string): Promise<{
  getCharacteristic(uuid: string): Promise<Characteristic>;
}> };
type Device = {
  id: string;
  name?: string;
  gatt?: { connect(): Promise<GattServer>; disconnect?(): void };
};
type NodeSlot = 'A' | 'B';
type BrowserBluetooth = {
  requestDevice(options: { filters: Array<{ services: string[] }> }): Promise<Device>;
};

// Use only devices selected for this test. A browser's older Bluetooth grants
// may refer to tablets that are no longer present or have been re-enrolled.
const selectedDevices = new Map<NodeSlot, Device>();

function bluetooth(): BrowserBluetooth {
  const available = (navigator as Navigator & { bluetooth?: BrowserBluetooth }).bluetooth;
  if (!available) throw new Error('Use a browser with Web Bluetooth, such as Chrome or Edge, on a Bluetooth-enabled computer.');
  return available;
}

export async function grantWorkplacePhone(slot: NodeSlot): Promise<number> {
  const api = bluetooth();
  const device = await api.requestDevice({ filters: [{ services: [SERVICE_UUID] }] });
  const otherSlot: NodeSlot = slot === 'A' ? 'B' : 'A';
  if (selectedDevices.get(otherSlot)?.id === device.id) {
    throw new Error(`This tablet is already selected for node ${otherSlot}. Choose the other tablet for node ${slot}.`);
  }
  selectedDevices.set(slot, device);
  return selectedDevices.size;
}

async function connectWithRetry(device: Device): Promise<GattServer> {
  if (!device.gatt) throw new Error('Bluetooth connection is unavailable');
  try {
    return await device.gatt.connect();
  } catch {
    device.gatt.disconnect?.();
    await new Promise(resolve => setTimeout(resolve, 500));
    return device.gatt.connect();
  }
}

function uuidBytes(value: string): Uint8Array {
  const hex = value.replaceAll('-', '');
  if (!/^[0-9a-f]{32}$/i.test(hex)) throw new Error('The login request ID is malformed.');
  return new Uint8Array(hex.match(/.{2}/g)!.map(pair => parseInt(pair, 16)));
}

export async function sendChallengeToGrantedPhones(challengeId: string): Promise<{ reached: number; granted: number; failures: string[] }> {
  const devices = [...selectedDevices.entries()];
  let reached = 0;
  const failures: string[] = [];
  for (const [slot, device] of devices) {
    let phase = 'connect';
    try {
      const server = await connectWithRetry(device);
      phase = 'find service';
      const service = await server.getPrimaryService(SERVICE_UUID);
      phase = 'find request channel';
      const characteristic = await service.getCharacteristic(REQUEST_UUID);
      const bytes = uuidBytes(challengeId);
      const request = bytes.buffer.slice(0) as ArrayBuffer;
      if (characteristic.properties?.writeWithoutResponse && characteristic.writeValueWithoutResponse) {
        phase = 'send request without response';
        await characteristic.writeValueWithoutResponse(request);
        // Give the BLE stack time to transmit before releasing the connection.
        await new Promise(resolve => setTimeout(resolve, 500));
      } else {
        phase = 'send request with response';
        await characteristic.writeValueWithResponse(request);
      }
      reached += 1;
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Bluetooth connection failed';
      failures.push(`Node ${slot}${device.name ? ` (${device.name})` : ''}, ${phase}: ${reason}`);
    } finally {
      device.gatt?.disconnect?.();
    }
  }
  return { reached, granted: devices.length, failures };
}
