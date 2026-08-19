#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace bicycle::csc {
inline constexpr std::uint16_t kServiceUuid = 0x1816;
inline constexpr std::uint16_t kMeasurementUuid = 0x2A5B;
inline constexpr std::uint16_t kFeatureUuid = 0x2A5C;
inline constexpr std::uint16_t kControlPointUuid = 0x2A55;

struct Measurement { std::array<std::uint8_t, 7> bytes{}; std::size_t size = 7; };

constexpr std::uint16_t event_time_1024(std::uint64_t timestamp_us) {
  // Reduce first so a long-running microsecond clock cannot overflow at *1024.
  return static_cast<std::uint16_t>(((timestamp_us % 64000000ULL) * 1024ULL) /
                                    1000000ULL);
}

constexpr Measurement encode_wheel_measurement(std::uint32_t revolutions,
                                                std::uint16_t event_time) {
  return {{{0x01, static_cast<std::uint8_t>(revolutions),
            static_cast<std::uint8_t>(revolutions >> 8),
            static_cast<std::uint8_t>(revolutions >> 16),
            static_cast<std::uint8_t>(revolutions >> 24),
            static_cast<std::uint8_t>(event_time),
            static_cast<std::uint8_t>(event_time >> 8)}}, 7};
}

class WheelState {
 public:
  void on_revolution(std::uint64_t timestamp_us) {
    if (revolutions_ != std::numeric_limits<std::uint32_t>::max()) ++revolutions_;
    last_event_time_ = event_time_1024(timestamp_us);
  }
  void set_cumulative(std::uint32_t value) { revolutions_ = value; }
  std::uint32_t revolutions() const { return revolutions_; }
  std::uint16_t last_event_time() const { return last_event_time_; }
  Measurement measurement() const { return encode_wheel_measurement(revolutions_, last_event_time_); }
 private:
  std::uint32_t revolutions_ = 0;
  std::uint16_t last_event_time_ = 0;
};
}  // namespace bicycle::csc
