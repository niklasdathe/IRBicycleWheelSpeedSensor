idf_component_register(
  SRCS "app_main.c" "ir_spoke_rmt_adapter.c"
       "ir_spoke_link_monitor.c"
       "ir_spoke_can_mcp2515_adapter.c"
  INCLUDE_DIRS "." "../include"
  REQUIRES driver esp_timer esp_driver_pcnt ir_spoke_core
           ir_spoke_ble_csc ir_spoke_debug
)
