# SPDX-License-Identifier: MIT
"""
Weighted pulse meter component for ESPHome.

Counts both ON and OFF edges from a single GPIO input, assigns different
liter weights to each edge, publishes flow (L/min) and total (L),
applies EMA smoothing, and zeros flow after a timeout.

YAML usage (example):

external_components:
  - source:
      type: local
      path: components

sensor:
  - platform: weighted_pulse_meter
    id: wpm
    pin: D1
    on_press_liters: 0.6       # OFF->ON
    on_release_liters: 0.4     # ON->OFF
    debounce: 10ms
    timeout: 150s
    ema_alpha: 0.25
    sample_interval: 5ms
    flow:
      name: "Water Usage"
      unit_of_measurement: "L/min"
      accuracy_decimals: 2
      icon: "mdi:waves-arrow-right"
    total:
      name: "Total Water"
      device_class: water
      state_class: total_increasing
      unit_of_measurement: "L"
      accuracy_decimals: 0
      icon: "mdi:water"
"""

from __future__ import annotations

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import gpio, sensor
from esphome.const import (
    CONF_ID,
    CONF_PIN,
    DEVICE_CLASS_WATER,
    ICON_WATER,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_EMPTY,
    UNIT_LITER,
    UNIT_LITER_PER_MINUTE,
)

CODEOWNERS = ["@you"]

weighted_ns = cg.esphome_ns.namespace("weighted_pulse_meter")
WeightedPulseMeter = weighted_ns.class_("WeightedPulseMeter", cg.Component)

# Custom keys
CONF_FLOW = "flow"
CONF_TOTAL = "total"
CONF_ON_PRESS_LITERS = "on_press_liters"
CONF_ON_RELEASE_LITERS = "on_release_liters"
CONF_DEBOUNCE = "debounce"
CONF_TIMEOUT = "timeout"
CONF_EMA_ALPHA = "ema_alpha"
CONF_SAMPLE_INTERVAL = "sample_interval"

# Defaults
DEFAULT_ON_PRESS_L = 0.6
DEFAULT_ON_RELEASE_L = 0.4
DEFAULT_DEBOUNCE_MS = "10ms"
DEFAULT_TIMEOUT = "150s"
DEFAULT_ALPHA = 0.25
DEFAULT_SAMPLE_INTERVAL = "5ms"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WeightedPulseMeter),
        cv.Required(CONF_PIN): gpio.gpio_input_pin_schema,
        cv.Optional(CONF_ON_PRESS_LITERS, default=DEFAULT_ON_PRESS_L): cv.float_,
        cv.Optional(CONF_ON_RELEASE_LITERS, default=DEFAULT_ON_RELEASE_L): cv.float_,
        cv.Optional(CONF_DEBOUNCE, default=DEFAULT_DEBOUNCE_MS): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_EMA_ALPHA, default=DEFAULT_ALPHA): cv.percentage,  # 0..1
        cv.Optional(CONF_SAMPLE_INTERVAL, default=DEFAULT_SAMPLE_INTERVAL): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_FLOW): sensor.sensor_schema(
            unit_of_measurement=UNIT_LITER_PER_MINUTE,
            accuracy_decimals=2,
            icon="mdi:waves-arrow-right",
        ),
        cv.Optional(CONF_TOTAL): sensor.sensor_schema(
            unit_of_measurement=UNIT_LITER,
            accuracy_decimals=0,
            device_class=DEVICE_CLASS_WATER,
            state_class=STATE_CLASS_TOTAL_INCREASING,
            icon=ICON_WATER,
        ),
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config: dict) -> None:
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    pin = await gpio.gpio_pin_expression(config[CONF_PIN])
    cg.add(var.set_pin(pin))

    cg.add(var.set_on_press_liters(config[CONF_ON_PRESS_LITERS]))
    cg.add(var.set_on_release_liters(config[CONF_ON_RELEASE_LITERS]))
    cg.add(var.set_debounce_ms(config[CONF_DEBOUNCE].total_milliseconds))
    cg.add(var.set_timeout_ms(config[CONF_TIMEOUT].total_milliseconds))
    cg.add(var.set_alpha(config[CONF_EMA_ALPHA]))
    cg.add(var.set_sample_interval_ms(config[CONF_SAMPLE_INTERVAL].total_milliseconds))

    if flow_cfg := config.get(CONF_FLOW):
        flow = await sensor.new_sensor(flow_cfg)
        cg.add(var.set_flow_sensor(flow))

    if total_cfg := config.get(CONF_TOTAL):
        total = await sensor.new_sensor(total_cfg)
        cg.add(var.set_total_sensor(total))
