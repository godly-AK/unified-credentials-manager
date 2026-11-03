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
type BrowserBluetooth = {
  getDevices?: () => Promise<Device[]>;
  requestDevice(options: { filters: Array<{ services: string[] }> }): Promise<Device>;
};

// Contact only devices this account explicitly selected. Browser IDs are opaque,
// and the backend still decides whether each signing key is enrolled and distinct.
const selectedDevices = new Map<string, Device>();
let selectedAccount = '';

function setAccount(username: string): void {
  if (selectedAccount !== username) {
    selectedDevices.clear();
    selectedAccount = username;
  }
}

function storageKey(username: string): string {
  return `ucm-workplace-choices-v2:${username}`;
}

function savedIds(username: string): string[] {
  try {
    const current: unknown = JSON.parse(localStorage.getItem(storageKey(username)) || 'null');
    if (Array.isArray(current)) return current.filter((id): id is string => typeof id === 'string');
    const legacy: unknown = JSON.parse(localStorage.getItem(`ucm-workplace-choices-v1:${username}`) || '{}');
    if (legacy && typeof legacy === 'object') return Object.values(legacy).filter((id): id is string => typeof id === 'string');
    return [];
  } catch { return []; }
}

function saveIds(username: string): void {
  try {
    localStorage.setItem(storageKey(username), JSON.stringify([...new Set([...savedIds(username), ...selectedDevices.keys()])]));
  } catch { /* A private browser window can still use this tab's selections. */ }
}

function bluetooth(): BrowserBluetooth {
  const available = (navigator as Navigator & { bluetooth?: BrowserBluetooth }).bluetooth;
  if (!available) throw new Error('Use a browser with Web Bluetooth, such as Chrome or Edge, on a Bluetooth-enabled computer.');
  return available;
}

export async function restoreWorkplacePhones(username: string): Promise<{ count: number; supported: boolean }> {
  setAccount(username);
  const api = bluetooth();
  if (typeof api.getDevices !== 'function') return { count: selectedDevices.size, supported: false };
  try {
    const devices = await api.getDevices();
    const ids = savedIds(username);
    for (const id of ids) {
      const device = devices.find(candidate => candidate.id === id);
      if (device) selectedDevices.set(id, device);
    }
  } catch { return { count: selectedDevices.size, supported: false }; }
  return { count: selectedDevices.size, supported: true };
}

export async function grantWorkplacePhone(username: string): Promise<number> {
  setAccount(username);
  const api = bluetooth();
  const device = await api.requestDevice({ filters: [{ services: [SERVICE_UUID] }] });
  selectedDevices.set(device.id, device);
  saveIds(username);
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

export async function sendChallengeToGrantedPhones(
  challengeId: string, username: string, onProgress?: (message: string) => void,
): Promise<{ reached: number; granted: number; failures: string[] }> {
  await restoreWorkplacePhones(username);
  const devices = [...selectedDevices.values()];
  if (devices.length === 0) onProgress?.('No selected trusted nodes are available. Choose nearby nodes once in this browser.');
  let reached = 0;
  const failures: string[] = [];
  for (const device of devices) {
    let phase = 'connect';
    onProgress?.(`Connecting to trusted node${device.name ? ` (${device.name})` : ''}…`);
    try {
      const server = await connectWithRetry(device);
      phase = 'find service';
      onProgress?.('Node connected. Finding its request channel…');
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
      onProgress?.('Request sent to a node. Waiting for its signed approval…');
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Bluetooth connection failed';
      failures.push(`Node${device.name ? ` (${device.name})` : ''}, ${phase}: ${reason}`);
      onProgress?.(`A node could not be contacted: ${reason}`);
    } finally {
      device.gatt?.disconnect?.();
    }
  }
  return { reached, granted: devices.length, failures };
}
