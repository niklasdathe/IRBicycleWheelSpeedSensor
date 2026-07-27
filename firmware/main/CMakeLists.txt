idf_component_register(
  SRCS "app_main.c" "ir_spoke_rmt_adapter.c"
  INCLUDE_DIRS "." "../include"
  REQUIRES driver esp_timer ir_spoke_core
)
