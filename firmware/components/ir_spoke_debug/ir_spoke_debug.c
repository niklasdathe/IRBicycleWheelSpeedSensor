#include "ir_spoke_debug.h"

#include <stdarg.h>
#include <stdbool.h>
#include <stdio.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_timer.h"
#include "sdkconfig.h"

#define DEBUG_TAG "ir_debug"
#define DEBUG_MESSAGE_SIZE 224

static bool initialized;

#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE) && defined(CONFIG_IR_SPOKE_DEBUG_LED)
static esp_timer_handle_t led_off_timer;

static int led_level(bool on) {
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_ACTIVE_LOW
    return on ? 0 : 1;
#else
    return on ? 1 : 0;
#endif
}

static void led_off(void *argument) {
    (void)argument;
    gpio_set_level((gpio_num_t)CONFIG_IR_SPOKE_DEBUG_LED_GPIO,
                   led_level(false));
}
#endif

static const char *event_name(ir_spoke_debug_event_t event) {
    switch (event) {
        case IR_SPOKE_DEBUG_STARTUP: return "startup";
        case IR_SPOKE_DEBUG_RMT: return "rmt";
        case IR_SPOKE_DEBUG_RMT_CAPTURE: return "rmt-capture";
        case IR_SPOKE_DEBUG_PULSE_ACCEPTED: return "pulse-ok";
        case IR_SPOKE_DEBUG_PULSE_REJECTED: return "pulse-reject";
        case IR_SPOKE_DEBUG_ESTIMATOR: return "estimator";
        case IR_SPOKE_DEBUG_REVOLUTION: return "revolution";
        case IR_SPOKE_DEBUG_BLE: return "ble";
        case IR_SPOKE_DEBUG_BLE_NOTIFY: return "ble-notify";
        case IR_SPOKE_DEBUG_CAN: return "can";
        case IR_SPOKE_DEBUG_CAN_TX: return "can-tx";
        case IR_SPOKE_DEBUG_ERROR: return "error";
        default: return "unknown";
    }
}

static bool serial_enabled(ir_spoke_debug_event_t event) {
#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE) && defined(CONFIG_IR_SPOKE_DEBUG_SERIAL)
    switch (event) {
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_STARTUP
        case IR_SPOKE_DEBUG_STARTUP: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_RMT
        case IR_SPOKE_DEBUG_RMT: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_RMT_CAPTURES
        case IR_SPOKE_DEBUG_RMT_CAPTURE: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_PULSE_ACCEPTED
        case IR_SPOKE_DEBUG_PULSE_ACCEPTED: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_PULSE_REJECTED
        case IR_SPOKE_DEBUG_PULSE_REJECTED: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_ESTIMATOR
        case IR_SPOKE_DEBUG_ESTIMATOR: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_REVOLUTION
        case IR_SPOKE_DEBUG_REVOLUTION: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_BLE
        case IR_SPOKE_DEBUG_BLE: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_BLE_NOTIFY
        case IR_SPOKE_DEBUG_BLE_NOTIFY: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_CAN
        case IR_SPOKE_DEBUG_CAN: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_CAN_TX
        case IR_SPOKE_DEBUG_CAN_TX: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL_ERRORS
        case IR_SPOKE_DEBUG_ERROR: return true;
#endif
        default: return false;
    }
#else
    (void)event;
    return false;
#endif
}

static bool led_enabled(ir_spoke_debug_event_t event) {
#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE) && defined(CONFIG_IR_SPOKE_DEBUG_LED)
    switch (event) {
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_STARTUP
        case IR_SPOKE_DEBUG_STARTUP: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_RMT
        case IR_SPOKE_DEBUG_RMT: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_PULSE_ACCEPTED
        case IR_SPOKE_DEBUG_PULSE_ACCEPTED: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_PULSE_REJECTED
        case IR_SPOKE_DEBUG_PULSE_REJECTED: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_ESTIMATOR
        case IR_SPOKE_DEBUG_ESTIMATOR: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_REVOLUTION
        case IR_SPOKE_DEBUG_REVOLUTION: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_BLE
        case IR_SPOKE_DEBUG_BLE: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_CAN
        case IR_SPOKE_DEBUG_CAN: return true;
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED_ERRORS
        case IR_SPOKE_DEBUG_ERROR: return true;
#endif
        default: return false;
    }
#else
    (void)event;
    return false;
#endif
}

static uint32_t led_pulse_ms(ir_spoke_debug_event_t event) {
    switch (event) {
        case IR_SPOKE_DEBUG_PULSE_ACCEPTED: return 15;
        case IR_SPOKE_DEBUG_PULSE_REJECTED: return 40;
        case IR_SPOKE_DEBUG_CAN_TX: return 20;
        case IR_SPOKE_DEBUG_REVOLUTION: return 100;
        case IR_SPOKE_DEBUG_STARTUP: return 100;
        case IR_SPOKE_DEBUG_RMT: return 150;
        case IR_SPOKE_DEBUG_ESTIMATOR: return 300;
        case IR_SPOKE_DEBUG_BLE: return 200;
        case IR_SPOKE_DEBUG_CAN: return 100;
        case IR_SPOKE_DEBUG_ERROR: return 700;
        default: return 50;
    }
}

static void signal_led(ir_spoke_debug_event_t event) {
#if defined(CONFIG_IR_SPOKE_DEBUG_ENABLE) && defined(CONFIG_IR_SPOKE_DEBUG_LED)
    if (!initialized || !led_off_timer || !led_enabled(event)) return;
    gpio_set_level((gpio_num_t)CONFIG_IR_SPOKE_DEBUG_LED_GPIO,
                   led_level(true));
    (void)esp_timer_stop(led_off_timer);
    (void)esp_timer_start_once(led_off_timer,
        (uint64_t)led_pulse_ms(event) * 1000ULL);
#else
    (void)event;
#endif
}

esp_err_t ir_spoke_debug_init(void) {
#ifdef CONFIG_IR_SPOKE_DEBUG_ENABLE
#if defined(CONFIG_IR_SPOKE_DEBUG_LED)
    const gpio_config_t led_config = {
        .pin_bit_mask = 1ULL << CONFIG_IR_SPOKE_DEBUG_LED_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t rc = gpio_config(&led_config);
    if (rc != ESP_OK) return rc;
    gpio_set_level((gpio_num_t)CONFIG_IR_SPOKE_DEBUG_LED_GPIO,
                   led_level(false));
    const esp_timer_create_args_t timer_args = {
        .callback = led_off,
        .name = "ir_dbg_led",
    };
    rc = esp_timer_create(&timer_args, &led_off_timer);
    if (rc != ESP_OK) return rc;
#endif
    initialized = true;
    ir_spoke_debug_event(IR_SPOKE_DEBUG_STARTUP,
        "debug enabled serial=%s led=%s",
#ifdef CONFIG_IR_SPOKE_DEBUG_SERIAL
        "yes",
#else
        "no",
#endif
#ifdef CONFIG_IR_SPOKE_DEBUG_LED
        "yes"
#else
        "no"
#endif
    );
#else
    initialized = true;
#endif
    return ESP_OK;
}

void ir_spoke_debug_event(ir_spoke_debug_event_t event,
                          const char *format, ...) {
#ifdef CONFIG_IR_SPOKE_DEBUG_ENABLE
    if (serial_enabled(event)) {
        char message[DEBUG_MESSAGE_SIZE];
        message[0] = '\0';
        if (format) {
            va_list args;
            va_start(args, format);
            (void)vsnprintf(message, sizeof(message), format, args);
            va_end(args);
        }
        if (event == IR_SPOKE_DEBUG_ERROR) {
            ESP_LOGE(DEBUG_TAG, "[%s] %s", event_name(event), message);
        } else {
            ESP_LOGI(DEBUG_TAG, "[%s] %s", event_name(event), message);
        }
    }
    signal_led(event);
#else
    (void)event;
    (void)format;
#endif
}
