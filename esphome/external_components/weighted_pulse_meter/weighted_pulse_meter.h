// SPDX-License-Identifier: MIT
#pragma once

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/gpio/gpio.h"
#include "esphome/core/preferences.h"
#include "esphome/core/log.h"

namespace esphome {
namespace weighted_pulse_meter {

class WeightedPulseMeter : public Component {
 public:
  void set_pin(gpio::GPIOPin *pin) { this->pin_ = pin; }

  void set_flow_sensor(sensor::Sensor *s) { this->flow_sensor_ = s; }
  void set_total_sensor(sensor::Sensor *s) { this->total_sensor_ = s; }

  void set_on_press_liters(float v) { this->on_press_l_ = v; }     // OFF->ON
  void set_on_release_liters(float v) { this->on_release_l_ = v; } // ON->OFF
  void set_debounce_ms(uint32_t v) { this->debounce_ms_ = v; }
  void set_timeout_ms(uint32_t v) { this->timeout_ms_ = v; }
  void set_alpha(float v) { this->alpha_ = v < 0.f ? 0.f : (v > 1.f ? 1.f : v); }
  void set_sample_interval_ms(uint32_t v) { this->sample_interval_ms_ = v; }

  // Runtime controls (optional to call from services/buttons etc.)
  void set_total(float liters);
  void set_weights(float on_press_l, float on_release_l);

  // Component
  void setup() override;
  void loop() override;
  void dump_config() override;

 protected:
  void publish_flow_(float lpm);
  void publish_total_();
  void add_volume_(float liters);
  void handle_edge_(bool new_state, uint32_t now);
  void check_timeout_(uint32_t now);
  void sample_pin_(uint32_t now);

  // Config
  gpio::GPIOPin *pin_{nullptr};
  sensor::Sensor *flow_sensor_{nullptr};
  sensor::Sensor *total_sensor_{nullptr};

  float on_press_l_{0.6f};
  float on_release_l_{0.4f};
  float alpha_{0.25f};

  uint32_t debounce_ms_{10};
  uint32_t timeout_ms_{150000};
  uint32_t sample_interval_ms_{5};

  // State
  bool debounced_state_{false};
  bool raw_state_{false};
  uint32_t last_raw_change_ms_{0};
  uint32_t last_debounced_change_ms_{0};
  uint32_t last_sample_ms_{0};
  bool initialized_{false};
  bool timed_out_zeroed_{false};
  bool has_flow_{false};

  float flow_lpm_{0.0f};
  float total_l_{0.0f};

  // Persistence
  ESPPreferenceObject pref_total_;
};

}  // namespace weighted_pulse_meter
}  // namespace esphome
