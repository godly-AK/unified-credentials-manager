package com.ucm.authenticator.security

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattServer
import android.bluetooth.BluetoothGattServerCallback
import android.bluetooth.BluetoothGattService
import android.bluetooth.BluetoothManager
import android.bluetooth.le.AdvertiseCallback
import android.bluetooth.le.AdvertiseData
import android.bluetooth.le.AdvertiseSettings
import android.content.Context
import android.content.pm.PackageManager
import android.os.ParcelUuid
import androidx.core.app.ActivityCompat
import com.ucm.authenticator.MainActivity
import com.ucm.authenticator.network.UcmApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.nio.ByteBuffer
import java.util.Base64
import java.util.UUID

class WorkplaceBleServer(
    private val activity: MainActivity,
    private val api: UcmApi,
    private val username: String,
    private val slot: String,
    private val nodeId: String,
    private val keys: WorkplaceNodeKeyManager,
    private val onStatus: (String) -> Unit,
) {
    companion object {
        val SERVICE_UUID: UUID = UUID.fromString("b15a0a00-571d-4a73-95de-6d660c00b001")
        val REQUEST_UUID: UUID = UUID.fromString("b15a0a01-571d-4a73-95de-6d660c00b001")
    }

    private val scope = CoroutineScope(Dispatchers.Main)
    private var gatt: BluetoothGattServer? = null
    private val manager = activity.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val advertiser get() = manager.adapter.bluetoothLeAdvertiser
    private val advertising = object : AdvertiseCallback() {
        override fun onStartSuccess(settingsInEffect: AdvertiseSettings) {
            scope.launch { onStatus("Trusted node is advertising. Keep this screen open.") }
        }
        override fun onStartFailure(errorCode: Int) {
            scope.launch { onStatus("Bluetooth advertising failed: $errorCode") }
        }
    }
    private val callback = object : BluetoothGattServerCallback() {
        @SuppressLint("MissingPermission")
        override fun onServiceAdded(status: Int, service: BluetoothGattService) {
            if (status != BluetoothGatt.GATT_SUCCESS) {
                scope.launch { onStatus("Cannot publish Bluetooth service: $status") }
                stop()
                return
            }
            val settings = AdvertiseSettings.Builder().setAdvertiseMode(AdvertiseSettings.ADVERTISE_MODE_LOW_LATENCY)
                .setConnectable(true).setTxPowerLevel(AdvertiseSettings.ADVERTISE_TX_POWER_MEDIUM).build()
            val data = AdvertiseData.Builder().addServiceUuid(ParcelUuid(SERVICE_UUID))
                .setIncludeDeviceName(false).build()
            advertiser?.startAdvertising(settings, data, advertising)
                ?: scope.launch { onStatus("Bluetooth advertising is unavailable on this phone.") }
        }

        @SuppressLint("MissingPermission")
        override fun onCharacteristicWriteRequest(device: BluetoothDevice, requestId: Int,
            characteristic: BluetoothGattCharacteristic, preparedWrite: Boolean,
            responseNeeded: Boolean, offset: Int, value: ByteArray) {
            val valid = characteristic.uuid == REQUEST_UUID && !preparedWrite && offset == 0 && value.size == 16
            if (responseNeeded) gatt?.sendResponse(device, requestId,
                if (valid) BluetoothGatt.GATT_SUCCESS else BluetoothGatt.GATT_INVALID_ATTRIBUTE_LENGTH, offset, null)
            if (!valid) return
            scope.launch { onStatus("Trusted node received a Bluetooth request. Checking UCM…") }
            val input = ByteBuffer.wrap(value)
            val id = UUID(input.long, input.long).toString()
            scope.launch {
                try {
                    val challenge = api.request("/api/trust/challenge/$id")
                    require(challenge.getString("username") == username) { "This request is for a different account." }
                    val signature = keys.sign(LoginTrustMessage.bytes("node-$slot", id, challenge.getString("nonce")))
                    api.request("/api/trust/node-approve", JSONObject()
                        .put("challenge_id", id).put("node_id", nodeId)
                        .put("signature_b64", Base64.getEncoder().encodeToString(signature)))
                    onStatus("Trusted node approved request $id")
                } catch (error: Exception) { onStatus(error.message ?: "Could not approve request.") }
            }
        }
    }

    @SuppressLint("MissingPermission")
    fun start() {
        val required = listOf(Manifest.permission.BLUETOOTH_ADVERTISE, Manifest.permission.BLUETOOTH_CONNECT)
        if (required.any { ActivityCompat.checkSelfPermission(activity, it) != PackageManager.PERMISSION_GRANTED }) {
            ActivityCompat.requestPermissions(activity, required.toTypedArray(), 44)
            error("Grant Nearby devices permission, then press Start again.")
        }
        check(manager.adapter.isEnabled) { "Turn on Bluetooth first." }
        check(manager.adapter.isMultipleAdvertisementSupported) { "This phone cannot advertise as a workplace node." }
        val server = manager.openGattServer(activity, callback) ?: error("Cannot open Bluetooth service.")
        val service = BluetoothGattService(SERVICE_UUID, BluetoothGattService.SERVICE_TYPE_PRIMARY)
        val request = BluetoothGattCharacteristic(REQUEST_UUID,
            BluetoothGattCharacteristic.PROPERTY_WRITE or BluetoothGattCharacteristic.PROPERTY_WRITE_NO_RESPONSE,
            BluetoothGattCharacteristic.PERMISSION_WRITE)
        service.addCharacteristic(request)
        gatt = server
        check(server.addService(service)) { "Cannot publish Bluetooth service." }
        onStatus("Starting trusted node. Keep this screen open.")
    }

    @SuppressLint("MissingPermission")
    fun stop() {
        if (ActivityCompat.checkSelfPermission(activity, Manifest.permission.BLUETOOTH_ADVERTISE) == PackageManager.PERMISSION_GRANTED) {
            advertiser?.stopAdvertising(advertising)
        }
        gatt?.close()
        gatt = null
    }
}
