// ESP-IDF 5.x example: continuous 38 kHz carrier and active-low RMT capture.
#include "driver/rmt_tx.h"
#include "driver/rmt_rx.h"
#include "driver/gpio.h"

static constexpr gpio_num_t TX_GPIO = GPIO_NUM_1;
static constexpr gpio_num_t RX_GPIO = GPIO_NUM_2;
static constexpr uint32_t RMT_RESOLUTION_HZ = 1000000; // 1 tick = 1 us
static constexpr uint32_t GLITCH_FILTER_US = 80;
static constexpr uint32_t VALID_LOW_MIN_US = 400;
static constexpr uint32_t VALID_LOW_MAX_US = 1200;
static constexpr uint32_t LINK_LOSS_US = 10000;

// Use rmt_apply_carrier() with 38 kHz, 50% duty on TX_GPIO and transmit
// 30-cycle bursts (~789 us) separated by 600 us gaps. This respects the
// receiver AGC envelope-duty constraints; do not send an uninterrupted carrier.
// RX uses:
//   signal_range_min_ns = GLITCH_FILTER_US * 1000
//   signal_range_max_ns = LINK_LOSS_US * 1000
//
// Accept active-low pulses in [400, 1200] us. Spoke-corrupted bursts are
// discarded. Declare link loss only when no valid low pulse arrives for 10 ms.
