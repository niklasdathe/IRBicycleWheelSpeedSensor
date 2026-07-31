#pragma once
#include <cstdint>
#include "freertos/FreeRTOS.h"
#include "csc_measurement.hpp"

struct ble_gap_event;

namespace bicycle::csc {
class NimbleService {
 public:
  int register_service();
  // Call after NimBLE host synchronization. This starts standards-aligned,
  // connectable GAP advertising and owns subsequent reconnect advertising.
  int start_advertising();
  void on_wheel_revolution(std::uint64_t timestamp_us);
  int notify();
  void set_cumulative(std::uint32_t value);
  bool begin_control_procedure(std::uint16_t connection_handle);
  void cancel_control_procedure();
  bool control_indications_enabled(std::uint16_t connection_handle);
  static NimbleService& instance();
 private:
  static int gap_event(::ble_gap_event* event, void* arg);
  WheelState state_{};
  std::uint16_t connection_handle_ = 0xFFFF;
  std::uint16_t control_connection_handle_ = 0xFFFF;
  bool control_procedure_in_progress_ = false;
  bool measurement_subscribed_ = false;
  bool control_indications_enabled_ = false;
  bool registered_ = false;
  portMUX_TYPE state_lock_ = portMUX_INITIALIZER_UNLOCKED;
};
}  // namespace bicycle::csc
