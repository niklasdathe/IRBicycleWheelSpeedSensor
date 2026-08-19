idf_component_register(
  SRCS "ir_spoke_debug.c"
  INCLUDE_DIRS "include"
  REQUIRES esp_driver_gpio esp_timer log
)
