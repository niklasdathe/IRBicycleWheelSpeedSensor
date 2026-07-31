#include "ir_spoke_can_mcp2515_adapter.h"

#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "ir_spoke_generated_c.h"

#define MCP_RESET 0xC0u
#define MCP_READ 0x03u
#define MCP_WRITE 0x02u
#define MCP_BIT_MODIFY 0x05u
#define MCP_RTS_TX0 0x81u
#define MCP_CANSTAT 0x0Eu
#define MCP_CANCTRL 0x0Fu
#define MCP_CNF3 0x28u
#define MCP_CNF2 0x29u
#define MCP_CNF1 0x2Au
#define MCP_CANINTE 0x2Bu
#define MCP_TXB0CTRL 0x30u
#define MCP_TXB0SIDH 0x31u

_Static_assert(IR_SPOKE_TX_GPIO != IR_SPOKE_CAN_INT_GPIO,
               "IR TX conflicts with CAN INT");
_Static_assert(IR_SPOKE_RX_GPIO != IR_SPOKE_CAN_INT_GPIO,
               "IR RX conflicts with CAN INT");
_Static_assert(IR_SPOKE_TX_GPIO != IR_SPOKE_CAN_CS_GPIO,
               "IR TX conflicts with CAN CS");
_Static_assert(IR_SPOKE_RX_GPIO != IR_SPOKE_CAN_CS_GPIO,
               "IR RX conflicts with CAN CS");
_Static_assert(IR_SPOKE_TX_GPIO != IR_SPOKE_CAN_SCK_GPIO,
               "IR TX conflicts with CAN SCK");
_Static_assert(IR_SPOKE_RX_GPIO != IR_SPOKE_CAN_SCK_GPIO,
               "IR RX conflicts with CAN SCK");
_Static_assert(IR_SPOKE_TX_GPIO != IR_SPOKE_CAN_MISO_GPIO,
               "IR TX conflicts with CAN MISO");
_Static_assert(IR_SPOKE_RX_GPIO != IR_SPOKE_CAN_MISO_GPIO,
               "IR RX conflicts with CAN MISO");
_Static_assert(IR_SPOKE_TX_GPIO != IR_SPOKE_CAN_MOSI_GPIO,
               "IR TX conflicts with CAN MOSI");
_Static_assert(IR_SPOKE_RX_GPIO != IR_SPOKE_CAN_MOSI_GPIO,
               "IR RX conflicts with CAN MOSI");

static spi_device_handle_t device;

static esp_err_t transfer(const uint8_t *tx, uint8_t *rx, size_t length) {
    spi_transaction_t transaction = {
        .length = length * 8u,
        .tx_buffer = tx,
        .rx_buffer = rx,
    };
    return spi_device_transmit(device, &transaction);
}

static esp_err_t command(uint8_t opcode) {
    return transfer(&opcode, NULL, 1);
}

static esp_err_t write_registers(
    uint8_t address, const uint8_t *values, size_t count) {
    uint8_t packet[2 + 13] = {MCP_WRITE, address};
    if (count > 13u) return ESP_ERR_INVALID_SIZE;
    memcpy(&packet[2], values, count);
    return transfer(packet, NULL, count + 2u);
}

static esp_err_t bit_modify(uint8_t address, uint8_t mask, uint8_t value) {
    const uint8_t packet[] = {MCP_BIT_MODIFY, address, mask, value};
    return transfer(packet, NULL, sizeof(packet));
}

static esp_err_t read_register(uint8_t address, uint8_t *value) {
    const uint8_t tx[] = {MCP_READ, address, 0};
    uint8_t rx[sizeof(tx)] = {0};
    ESP_RETURN_ON_ERROR(transfer(tx, rx, sizeof(tx)), "ir_can", "read");
    *value = rx[2];
    return ESP_OK;
}

static int send_frame(void *context, const ir_spoke_can_frame_t *frame) {
    (void)context;
    if (!frame || frame->length > 8u || frame->identifier > 0x7FFu)
        return -1;
    uint8_t control = 0;
    if (read_register(MCP_TXB0CTRL, &control) != ESP_OK) return -2;
    if (control & 0x08u) return -3;

    uint8_t payload[13] = {
        (uint8_t)(frame->identifier >> 3),
        (uint8_t)(frame->identifier << 5),
        0, 0, frame->length,
    };
    memcpy(&payload[5], frame->data, frame->length);
    if (write_registers(
            MCP_TXB0SIDH, payload, 5u + frame->length) != ESP_OK)
        return -4;
    return command(MCP_RTS_TX0) == ESP_OK ? 0 : -5;
}

int ir_spoke_can_mcp2515_start(ir_spoke_can_transport_t *transport) {
    if (!transport) return -1;
    if (IR_SPOKE_CAN_OSCILLATOR_HZ != 16000000u ||
        IR_SPOKE_CAN_BITRATE_HZ != 500000u)
        return -2;

    const spi_bus_config_t bus = {
        .mosi_io_num = IR_SPOKE_CAN_MOSI_GPIO,
        .miso_io_num = IR_SPOKE_CAN_MISO_GPIO,
        .sclk_io_num = IR_SPOKE_CAN_SCK_GPIO,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 16,
    };
    ESP_RETURN_ON_ERROR(
        spi_bus_initialize(SPI2_HOST, &bus, SPI_DMA_DISABLED),
        "ir_can", "SPI bus");
    const spi_device_interface_config_t interface = {
        .clock_speed_hz = IR_SPOKE_CAN_SPI_CLOCK_HZ,
        .mode = 0,
        .spics_io_num = IR_SPOKE_CAN_CS_GPIO,
        .queue_size = 2,
    };
    ESP_RETURN_ON_ERROR(
        spi_bus_add_device(SPI2_HOST, &interface, &device),
        "ir_can", "SPI device");
    ESP_RETURN_ON_ERROR(command(MCP_RESET), "ir_can", "reset");
    vTaskDelay(pdMS_TO_TICKS(2));

    /* 16 MHz oscillator, 500 kbit/s, 16 TQ/bit, 68.75% sample point. */
    const uint8_t timing[] = {0x04, 0xA4, 0x00};
    ESP_RETURN_ON_ERROR(
        write_registers(MCP_CNF3, timing, sizeof(timing)),
        "ir_can", "bit timing");
    const uint8_t interrupts = 0x00;
    ESP_RETURN_ON_ERROR(
        write_registers(MCP_CANINTE, &interrupts, 1),
        "ir_can", "interrupt mask");
    ESP_RETURN_ON_ERROR(
        bit_modify(MCP_CANCTRL, 0xE0, 0x00),
        "ir_can", "normal mode");
    vTaskDelay(pdMS_TO_TICKS(2));
    uint8_t status = 0;
    ESP_RETURN_ON_ERROR(
        read_register(MCP_CANSTAT, &status), "ir_can", "mode status");
    if (status & 0xE0u) return -3;

    *transport = (ir_spoke_can_transport_t){
        .send = send_frame,
        .context = NULL,
    };
    return 0;
}
