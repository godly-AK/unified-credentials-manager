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
  getDevices?: () => Promise<Device[]>;
  requestDevice(options: { filters: Array<{ services: string[] }> }): Promise<Device>;
};

// Use only devices selected for this test. A browser's older Bluetooth grants
// may refer to tablets that are no longer present or have been re-enrolled.
const selectedDevices = new Map<NodeSlot, Device>();
let selectedAccount = '';

function setAccount(username: string): void {
  if (selectedAccount !== username) {
    selectedDevices.clear();
    selectedAccount = username;
  }
}

function storageKey(username: string): string {
  return `ucm-workplace-choices-v1:${username}`;
}

function savedIds(username: string): Partial<Record<NodeSlot, string>> {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(storageKey(username)) || '{}');
    if (!value || typeof value !== 'object') return {};
    const parsed = value as Record<string, unknown>;
    return {
      ...(typeof parsed.A === 'string' ? { A: parsed.A } : {}),
      ...(typeof parsed.B === 'string' ? { B: parsed.B } : {}),
    };
  } catch { return {}; }
}

function saveIds(username: string): void {
  try {
    localStorage.setItem(storageKey(username), JSON.stringify({
      ...savedIds(username),
      ...Object.fromEntries([...selectedDevices].map(([slot, device]) => [slot, device.id])),
    }));
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
    for (const slot of ['A', 'B'] as const) {
      const device = devices.find(candidate => candidate.id === ids[slot]);
      if (device) selectedDevices.set(slot, device);
    }
  } catch { return { count: selectedDevices.size, supported: false }; }
  return { count: selectedDevices.size, supported: true };
}

export async function grantWorkplacePhone(slot: NodeSlot, username: string): Promise<number> {
  setAccount(username);
  const api = bluetooth();
  const device = await api.requestDevice({ filters: [{ services: [SERVICE_UUID] }] });
  const otherSlot: NodeSlot = slot === 'A' ? 'B' : 'A';
  if (selectedDevices.get(otherSlot)?.id === device.id) {
    throw new Error(`This tablet is already selected for node ${otherSlot}. Choose the other tablet for node ${slot}.`);
  }
  selectedDevices.set(slot, device);
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
  const devices = [...selectedDevices.entries()];
  if (devices.length === 0) onProgress?.('No saved tablets are available. Select node A and node B once in this browser.');
  let reached = 0;
  const failures: string[] = [];
  for (const [slot, device] of devices) {
    let phase = 'connect';
    onProgress?.(`Connecting to node ${slot}${device.name ? ` (${device.name})` : ''}…`);
    try {
      const server = await connectWithRetry(device);
      phase = 'find service';
      onProgress?.(`Node ${slot} connected. Finding its request channel…`);
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
      onProgress?.(`Request sent to node ${slot}. Waiting for its signed approval…`);
    } catch (error) {
      const reason = error instanceof Error ? error.message : 'Bluetooth connection failed';
      failures.push(`Node ${slot}${device.name ? ` (${device.name})` : ''}, ${phase}: ${reason}`);
      onProgress?.(`Node ${slot} could not be contacted: ${reason}`);
    } finally {
      device.gatt?.disconnect?.();
    }
  }
  return { reached, granted: devices.length, failures };
}
