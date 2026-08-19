#include "csc_nimble_service.hpp"
#include <cstring>
extern "C" {
#include "ir_spoke_ble_csc.h"
#include "ir_spoke_debug.h"
#include "host/ble_gap.h"
#include "host/ble_gatt.h"
#include "host/ble_hs.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include "nvs_flash.h"
#include "os/os_mbuf.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
}

namespace bicycle::csc {
namespace {
std::uint16_t measurement_handle;
std::uint16_t control_point_handle;
const ble_uuid16_t service_uuid = BLE_UUID16_INIT(kServiceUuid);
const ble_uuid16_t measurement_uuid = BLE_UUID16_INIT(kMeasurementUuid);
const ble_uuid16_t feature_uuid = BLE_UUID16_INIT(kFeatureUuid);
const ble_uuid16_t control_point_uuid = BLE_UUID16_INIT(kControlPointUuid);
constexpr std::uint8_t kProcedureAlreadyInProgress = 0x80;
constexpr std::uint8_t kCccdImproperlyConfigured = 0x81;

int append(ble_gatt_access_ctxt* ctxt, const void* value, std::uint16_t size) {
  return os_mbuf_append(ctxt->om, value, size) == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
}

int access(std::uint16_t conn, std::uint16_t attr, ble_gatt_access_ctxt* ctxt, void*) {
  auto& service = NimbleService::instance();
  if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
    const std::uint8_t wheel_only_feature[] = {0x01, 0x00};
    return append(ctxt, wheel_only_feature, sizeof wheel_only_feature);
  }
  if (ctxt->op != BLE_GATT_ACCESS_OP_WRITE_CHR || attr != control_point_handle)
    return BLE_ATT_ERR_UNLIKELY;

  if (!service.control_indications_enabled(conn))
    return kCccdImproperlyConfigured;

  if (!service.begin_control_procedure(conn)) return kProcedureAlreadyInProgress;

  std::uint8_t request[5]{};
  const auto length = OS_MBUF_PKTLEN(ctxt->om);
  if (length < 1 || os_mbuf_copydata(ctxt->om, 0, 1, request) != 0) {
    service.cancel_control_procedure();
    return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
  }

  std::uint8_t result = 0x02;  // Op Code Not Supported
  if (request[0] == 0x01) {    // Set Cumulative Value
    if (length == sizeof request &&
        os_mbuf_copydata(ctxt->om, 0, length, request) == 0) {
      const std::uint32_t value = request[1] | (std::uint32_t{request[2]} << 8) |
                                  (std::uint32_t{request[3]} << 16) |
                                  (std::uint32_t{request[4]} << 24);
      service.set_cumulative(value);
      result = 0x01;  // Success
      ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                           "CSC cumulative wheel value set to %lu",
                           static_cast<unsigned long>(value));
    } else {
      result = 0x04;  // Operation Failed
    }
  }
  const std::uint8_t response[] = {0x10, request[0], result};
  auto* om = ble_hs_mbuf_from_flat(response, sizeof response);
  if (!om) {
    service.cancel_control_procedure();
    return BLE_ATT_ERR_INSUFFICIENT_RES;
  }
  const int rc = ble_gatts_indicate_custom(conn, control_point_handle, om);
  if (rc != 0) {
    service.cancel_control_procedure();
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "BLE control-point indication failed rc=%d", rc);
  }
  return rc == 0 ? 0 : BLE_ATT_ERR_UNLIKELY;
}

const ble_gatt_chr_def characteristics[] = {
    {&measurement_uuid.u, access, nullptr, nullptr, BLE_GATT_CHR_F_NOTIFY, 0,
     &measurement_handle, nullptr},
    {&feature_uuid.u, access, nullptr, nullptr, BLE_GATT_CHR_F_READ, 0,
     nullptr, nullptr},
    {&control_point_uuid.u, access, nullptr, nullptr,
     BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_INDICATE, 0,
     &control_point_handle, nullptr},
    {nullptr, nullptr, nullptr, nullptr, 0, 0, nullptr, nullptr}};
const ble_gatt_svc_def services[] = {
    {BLE_GATT_SVC_TYPE_PRIMARY, &service_uuid.u, nullptr, characteristics},
    {0, nullptr, nullptr, nullptr}};
}  // namespace

NimbleService& NimbleService::instance() { static NimbleService value; return value; }
int NimbleService::register_service() {
  if (registered_) return BLE_HS_EALREADY;
  const int rc = ble_gatts_count_cfg(services);
  if (rc != 0) return rc;
  const int add_rc = ble_gatts_add_svcs(services);
  if (add_rc == 0) registered_ = true;
  return add_rc;
}

int NimbleService::start_advertising() {
  // Cycling Speed Sensor appearance, Bluetooth Assigned Numbers 0x0482.
  ble_svc_gap_device_name_set("Bicycle Speed Sensor");
  ble_svc_gap_device_appearance_set(0x0482);

  static const ble_uuid16_t csc_uuid = BLE_UUID16_INIT(kServiceUuid);
  ble_hs_adv_fields fields{};
  fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
  fields.uuids16 = &csc_uuid;
  fields.num_uuids16 = 1;
  fields.uuids16_is_complete = 1;
  int rc = ble_gap_adv_set_fields(&fields);
  if (rc != 0) return rc;

  ble_hs_adv_fields scan_response{};
  scan_response.name = reinterpret_cast<const std::uint8_t*>(ble_svc_gap_device_name());
  scan_response.name_len = static_cast<std::uint8_t>(strlen(ble_svc_gap_device_name()));
  scan_response.name_is_complete = 1;
  scan_response.appearance = 0x0482;
  scan_response.appearance_is_present = 1;
  rc = ble_gap_adv_rsp_set_fields(&scan_response);
  if (rc != 0) return rc;

  std::uint8_t own_address_type = 0;
  rc = ble_hs_id_infer_auto(0, &own_address_type);
  if (rc != 0) return rc;
  ble_gap_adv_params parameters{};
  parameters.conn_mode = BLE_GAP_CONN_MODE_UND;
  parameters.disc_mode = BLE_GAP_DISC_MODE_GEN;
  // 30-60 ms is the profile's recommended initial advertising range.
  parameters.itvl_min = 0x0030;
  parameters.itvl_max = 0x0060;
  rc = ble_gap_adv_start(own_address_type, nullptr, BLE_HS_FOREVER,
                         &parameters, gap_event, this);
  if (rc == 0) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                         "advertising active as 'Bicycle Speed Sensor'");
  } else {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "BLE advertising start failed rc=%d", rc);
  }
  return rc;
}

int NimbleService::gap_event(ble_gap_event* event, void* arg) {
  auto& service = *static_cast<NimbleService*>(arg);
  switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
      if (event->connect.status == 0) {
        portENTER_CRITICAL(&service.state_lock_);
        service.connection_handle_ = event->connect.conn_handle;
        portEXIT_CRITICAL(&service.state_lock_);
        ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                             "connected handle=%u",
                             event->connect.conn_handle);
        return 0;
      }
      ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                           "BLE connection failed status=%d; restarting advertising",
                           event->connect.status);
      return service.start_advertising();
    case BLE_GAP_EVENT_DISCONNECT:
      ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                           "disconnected reason=%d; restarting advertising",
                           event->disconnect.reason);
      portENTER_CRITICAL(&service.state_lock_);
      service.connection_handle_ = BLE_HS_CONN_HANDLE_NONE;
      service.control_connection_handle_ = BLE_HS_CONN_HANDLE_NONE;
      service.control_procedure_in_progress_ = false;
      service.measurement_subscribed_ = false;
      service.control_indications_enabled_ = false;
      portEXIT_CRITICAL(&service.state_lock_);
      return service.start_advertising();
    case BLE_GAP_EVENT_NOTIFY_TX:
      if (event->notify_tx.indication &&
          event->notify_tx.attr_handle == control_point_handle) {
        portENTER_CRITICAL(&service.state_lock_);
        if (service.control_connection_handle_ == event->notify_tx.conn_handle) {
          service.control_procedure_in_progress_ = false;
          service.control_connection_handle_ = BLE_HS_CONN_HANDLE_NONE;
        }
        portEXIT_CRITICAL(&service.state_lock_);
      }
      return 0;
    case BLE_GAP_EVENT_SUBSCRIBE:
      if (event->subscribe.attr_handle == measurement_handle) {
        portENTER_CRITICAL(&service.state_lock_);
        service.measurement_subscribed_ = event->subscribe.cur_notify != 0;
        portEXIT_CRITICAL(&service.state_lock_);
        ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                             "CSC measurement notifications %s",
                             event->subscribe.cur_notify ? "enabled" : "disabled");
      } else if (event->subscribe.attr_handle == control_point_handle) {
        portENTER_CRITICAL(&service.state_lock_);
        service.control_indications_enabled_ = event->subscribe.cur_indicate != 0;
        portEXIT_CRITICAL(&service.state_lock_);
        ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                             "CSC control-point indications %s",
                             event->subscribe.cur_indicate ? "enabled" : "disabled");
      }
      return 0;
    default:
      return 0;
  }
}

void NimbleService::on_wheel_revolution(std::uint64_t us) {
  portENTER_CRITICAL(&state_lock_);
  state_.on_revolution(us);
  portEXIT_CRITICAL(&state_lock_);
}

void NimbleService::set_cumulative(std::uint32_t value) {
  portENTER_CRITICAL(&state_lock_);
  state_.set_cumulative(value);
  portEXIT_CRITICAL(&state_lock_);
}

bool NimbleService::begin_control_procedure(std::uint16_t connection_handle) {
  portENTER_CRITICAL(&state_lock_);
  const bool available = !control_procedure_in_progress_;
  if (available) {
    control_procedure_in_progress_ = true;
    control_connection_handle_ = connection_handle;
  }
  portEXIT_CRITICAL(&state_lock_);
  return available;
}

void NimbleService::cancel_control_procedure() {
  portENTER_CRITICAL(&state_lock_);
  control_procedure_in_progress_ = false;
  control_connection_handle_ = BLE_HS_CONN_HANDLE_NONE;
  portEXIT_CRITICAL(&state_lock_);
}

bool NimbleService::control_indications_enabled(std::uint16_t connection_handle) {
  portENTER_CRITICAL(&state_lock_);
  const bool enabled = connection_handle_ == connection_handle &&
                       control_indications_enabled_;
  portEXIT_CRITICAL(&state_lock_);
  return enabled;
}

int NimbleService::notify() {
  portENTER_CRITICAL(&state_lock_);
  const auto connection = connection_handle_;
  const bool subscribed = measurement_subscribed_;
  const auto value = state_.measurement();
  portEXIT_CRITICAL(&state_lock_);
  if (connection == BLE_HS_CONN_HANDLE_NONE || !subscribed) return BLE_HS_ENOTCONN;
  auto* om = ble_hs_mbuf_from_flat(value.bytes.data(), value.size);
  if (!om) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "BLE CSC notification allocation failed");
    return BLE_HS_ENOMEM;
  }
  const int rc = ble_gatts_notify_custom(connection, measurement_handle, om);
  if (rc == 0) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE_NOTIFY,
                         "CSC measurement notified handle=%u bytes=%u",
                         connection, value.size);
  } else {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "BLE CSC notification failed rc=%d", rc);
  }
  return rc;
}
}  // namespace bicycle::csc

namespace {
std::uint64_t last_notification_us;

void on_nimble_sync() {
  ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                       "NimBLE host synchronized");
  (void)bicycle::csc::NimbleService::instance().start_advertising();
}

void nimble_host_task(void*) {
  nimble_port_run();
  nimble_port_freertos_deinit();
}
}  // namespace

extern "C" int ir_spoke_ble_csc_start(void) {
  ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                       "initializing NimBLE CSC service");
  esp_err_t rc = nvs_flash_init();
  if (rc == ESP_ERR_NVS_NO_FREE_PAGES || rc == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                         "NVS requires erase/reinitialize");
    rc = nvs_flash_erase();
    if (rc == ESP_OK) rc = nvs_flash_init();
  }
  if (rc != ESP_OK) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "NVS initialization for BLE failed rc=%d", rc);
    return rc;
  }
  rc = nimble_port_init();
  if (rc != ESP_OK) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "nimble_port_init failed rc=%d", rc);
    return rc;
  }
  ble_svc_gap_init();
  ble_svc_gatt_init();
  rc = bicycle::csc::NimbleService::instance().register_service();
  if (rc != 0) {
    ir_spoke_debug_event(IR_SPOKE_DEBUG_ERROR,
                         "CSC service registration failed rc=%d", rc);
    return rc;
  }
  ble_hs_cfg.sync_cb = on_nimble_sync;
  nimble_port_freertos_init(nimble_host_task);
  ir_spoke_debug_event(IR_SPOKE_DEBUG_BLE,
                       "NimBLE host task started; waiting for sync");
  return 0;
}

extern "C" void ir_spoke_ble_csc_on_wheel_revolution(std::uint64_t timestamp_us) {
  auto& service = bicycle::csc::NimbleService::instance();
  service.on_wheel_revolution(timestamp_us);
  if (timestamp_us - last_notification_us >= 1000000ULL) {
    last_notification_us = timestamp_us;
    (void)service.notify();
  }
}
