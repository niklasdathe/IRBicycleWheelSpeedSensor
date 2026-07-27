// ESP-IDF implementation sketch. Constants are generated from system.json.
#include "driver/rmt_rx.h"
#include "driver/rmt_tx.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "ir_spoke_generated.h"
#include "spoke_learner.h"

namespace {
constexpr gpio_num_t kTxGpio = GPIO_NUM_1;
constexpr gpio_num_t kRxGpio = GPIO_NUM_2;
ir_spoke::SpokeLearner g_learner;

// The comparator emits the raw 38 kHz carrier. RMT RX removes that carrier in
// hardware and reports the missing-carrier windows caused by spokes. This is
// preferable to MCPWM capture here: MCPWM would interrupt on every 38 kHz edge
// unless another external envelope stage were added.
void configure_rmt(rmt_channel_handle_t* tx, rmt_channel_handle_t* rx) {
  rmt_tx_channel_config_t tx_cfg = {
      .gpio_num = kTxGpio,
      .clk_src = RMT_CLK_SRC_DEFAULT,
      .resolution_hz = ir_spoke::generated::kRmtResolutionHz,
      .mem_block_symbols = 64,
      .trans_queue_depth = 4,
  };
  ESP_ERROR_CHECK(rmt_new_tx_channel(&tx_cfg, tx));

  rmt_rx_channel_config_t rx_cfg = {
      .gpio_num = kRxGpio,
      .clk_src = RMT_CLK_SRC_DEFAULT,
      .resolution_hz = ir_spoke::generated::kRmtResolutionHz,
      .mem_block_symbols = 64,
      .flags = {.invert_in = false, .with_dma = false},
  };
  ESP_ERROR_CHECK(rmt_new_rx_channel(&rx_cfg, rx));

  rmt_carrier_config_t tx_carrier = {
      .frequency_hz = ir_spoke::generated::kCarrierHz,
      .duty_cycle = ir_spoke::generated::kCarrierDuty,
      .flags = {.polarity_active_low = false, .always_on = true},
  };
  ESP_ERROR_CHECK(rmt_apply_carrier(*tx, &tx_carrier));

  // Espressif explicitly recommends an RX demod frequency below the nominal
  // TX carrier to allow waveform distortion; this value is generated.
  rmt_carrier_config_t rx_demod = {
      .frequency_hz = ir_spoke::generated::kRxDemodFrequencyHz,
      .duty_cycle = 0.5f,
      .flags = {.polarity_active_low = false},
  };
  ESP_ERROR_CHECK(rmt_apply_carrier(*rx, &rx_demod));
  ESP_ERROR_CHECK(rmt_enable(*tx));
  ESP_ERROR_CHECK(rmt_enable(*rx));
}

void consume_blockage(std::uint32_t duration_us) {
  if (duration_us < ir_spoke::generated::kMinimumBlockedUs ||
      duration_us > ir_spoke::generated::kMaximumBlockedUs) {
    return;
  }
  // The edge timestamp, not the task wake-up time, is used in production.
  g_learner.ingest(static_cast<std::uint64_t>(esp_timer_get_time()));
}
}  // namespace

extern "C" void app_main(void) {
  rmt_channel_handle_t tx = nullptr;
  rmt_channel_handle_t rx = nullptr;
  configure_rmt(&tx, &rx);
  // Integrate consume_blockage() with rmt_rx_done_event_data_t. Keep receive
  // buffers in SRAM and immediately restart rmt_receive() in the callback/task.
}
