#ifndef IR_SPOKE_CAN_MCP2515_ADAPTER_H
#define IR_SPOKE_CAN_MCP2515_ADAPTER_H

#include "ir_spoke_can.h"

/* ESP-IDF/SPI boundary for the official Seeed XIAO CAN expansion board. */
int ir_spoke_can_mcp2515_start(ir_spoke_can_transport_t *transport);

#endif
