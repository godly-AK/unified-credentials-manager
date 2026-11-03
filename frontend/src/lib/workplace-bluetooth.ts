const SERVICE_UUID = 'b15a0a00-571d-4a73-95de-6d660c00b001';
const REQUEST_UUID = 'b15a0a01-571d-4a73-95de-6d660c00b001';

type Characteristic = {
  writeValueWithResponse(value: BufferSource): Promise<void>;
};
type Device = {
  id: string;
  name?: string;
  gatt?: { connect(): Promise<{ getPrimaryService(uuid: string): Promise<{
    getCharacteristic(uuid: string): Promise<Characteristic>;
  }> }> };
};
type BrowserBluetooth = {
  requestDevice(options: { filters: Array<{ services: string[] }> }): Promise<Device>;
};

// Use only devices selected for this test. A browser's older Bluetooth grants
// may refer to tablets that are no longer present or have been re-enrolled.
const selectedDevices = new Map<string, Device>();

function bluetooth(): BrowserBluetooth {
  const available = (navigator as Navigator & { bluetooth?: BrowserBluetooth }).bluetooth;
  if (!available) throw new Error('Use a browser with Web Bluetooth, such as Chrome or Edge, on a Bluetooth-enabled computer.');
  return available;
}

export async function grantWorkplacePhone(): Promise<number> {
  const api = bluetooth();
  const device = await api.requestDevice({ filters: [{ services: [SERVICE_UUID] }] });
  selectedDevices.set(device.id, device);
  return selectedDevices.size;
}

function uuidBytes(value: string): Uint8Array {
  const hex = value.replaceAll('-', '');
  if (!/^[0-9a-f]{32}$/i.test(hex)) throw new Error('The login request ID is malformed.');
  return new Uint8Array(hex.match(/.{2}/g)!.map(pair => parseInt(pair, 16)));
}

export async function sendChallengeToGrantedPhones(challengeId: string): Promise<{ reached: number; granted: number; failures: string[] }> {
  const devices = [...selectedDevices.values()];
  let reached = 0;
  const failures: string[] = [];
  for (const [index, device] of devices.entries()) {
    try {
      const server = await device.gatt?.connect();
      if (!server) throw new Error('Bluetooth connection is unavailable');
      const service = await server.getPrimaryService(SERVICE_UUID);
      const characteristic = await service.getCharacteristic(REQUEST_UUID);
      const bytes = uuidBytes(challengeId);
      await characteristic.writeValueWithResponse(bytes.buffer.slice(0) as ArrayBuffer);
      reached += 1;
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Bluetooth connection failed';
      failures.push(`Phone ${index + 1}${device.name ? ` (${device.name})` : ''}: ${reason}`);
    }
  }
  return { reached, granted: devices.length, failures };
}
