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
  getDevices(): Promise<Device[]>;
  requestDevice(options: { filters: Array<{ services: string[] }> }): Promise<Device>;
};

function bluetooth(): BrowserBluetooth {
  const available = (navigator as Navigator & { bluetooth?: BrowserBluetooth }).bluetooth;
  if (!available) throw new Error('Use a browser with Web Bluetooth, such as Chrome or Edge, on a Bluetooth-enabled computer.');
  return available;
}

export async function grantWorkplacePhone(): Promise<number> {
  const api = bluetooth();
  await api.requestDevice({ filters: [{ services: [SERVICE_UUID] }] });
  return (await api.getDevices()).length;
}

function uuidBytes(value: string): Uint8Array {
  const hex = value.replaceAll('-', '');
  if (!/^[0-9a-f]{32}$/i.test(hex)) throw new Error('The login request ID is malformed.');
  return new Uint8Array(hex.match(/.{2}/g)!.map(pair => parseInt(pair, 16)));
}

export async function sendChallengeToGrantedPhones(challengeId: string): Promise<{ reached: number; granted: number }> {
  const devices = await bluetooth().getDevices();
  let reached = 0;
  for (const device of devices) {
    try {
      const server = await device.gatt?.connect();
      if (!server) continue;
      const service = await server.getPrimaryService(SERVICE_UUID);
      const characteristic = await service.getCharacteristic(REQUEST_UUID);
      const bytes = uuidBytes(challengeId);
      await characteristic.writeValueWithResponse(bytes.buffer.slice(0) as ArrayBuffer);
      reached += 1;
    } catch {
      // Previously granted devices can be switched off or out of range.
    }
  }
  return { reached, granted: devices.length };
}
