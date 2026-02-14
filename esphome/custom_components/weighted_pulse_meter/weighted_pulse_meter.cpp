// SPDX-License-Identifier: MIT
#include "weighted_pulse_meter.h"

namespace esphome {
namespace weighted_pulse_meter {

static const char *const TAG = "weighted_pulse_meter";

void WeightedPulseMeter::setup() {
  ESP_LOGCONFIG(TAG, "Setting up WeightedPulseMeter...");

  if (this->pin_ == nullptr) {
    ESP_LOGE(TAG, "No pin configured!");
    return;
  }
  this->pin_->setup();  // honors pullup/inverted from YAML

  // Initialize states
  this->raw_state_ = this->pin_->digital_read();
  this->debounced_state_ = this->raw_state_;
  const uint32_t now = millis();
  this->last_raw_change_ms_ = now;
  this->last_debounced_change_ms_ = now;
  this->last_sample_ms_ = now;

  // Restore total from flash (prefer new key, fall back to old key once)
  this->pref_total_ = this->make_entity_preference<float>();

  float saved = 0.0f;
  if (!this->pref_total_.load(&saved)) {
    // Legacy storage location (pre-migration)
    auto legacy_pref = global_preferences->make_preference<float>(this->get_object_id_hash());
    if (legacy_pref.load(&saved)) {
      // Migrate forward so next boot uses the new key
      this->pref_total_.save(&saved);
    }
  }

this->total_l_ = saved;

  // Publish initial states
  if (this->flow_sensor_ != nullptr) this->flow_sensor_->publish_state(this->flow_lpm_);
  if (this->total_sensor_ != nullptr) this->total_sensor_->publish_state(this->total_l_);

  this->initialized_ = false;  // first valid edge will initialize timing
  this->timed_out_zeroed_ = false;
  this->has_flow_ = false;

  ESP_LOGCONFIG(TAG, "on_press_liters=%.3f, on_release_liters=%.3f, debounce=%ums, timeout=%ums, alpha=%.3f, sample_interval=%ums",
                this->on_press_l_, this->on_release_l_, this->debounce_ms_, this->timeout_ms_, this->alpha_, this->sample_interval_ms_);
}

void WeightedPulseMeter::dump_config() {
  ESP_LOGCONFIG(TAG, "WeightedPulseMeter:");
  LOG_PIN("  Pin: ", this->pin_);
  ESP_LOGCONFIG(TAG, "  on_press_liters: %.3f", this->on_press_l_);
  ESP_LOGCONFIG(TAG, "  on_release_liters: %.3f", this->on_release_l_);
  ESP_LOGCONFIG(TAG, "  debounce: %u ms", this->debounce_ms_);
  ESP_LOGCONFIG(TAG, "  timeout: %u ms", this->timeout_ms_);
  ESP_LOGCONFIG(TAG, "  ema_alpha: %.3f", this->alpha_);
  ESP_LOGCONFIG(TAG, "  sample_interval: %u ms", this->sample_interval_ms_);
}

void WeightedPulseMeter::loop() {
  const uint32_t now = millis();

  // Sample pin at a controlled interval to keep CPU usage predictable.
  if (now - this->last_sample_ms_ >= this->sample_interval_ms_) {
    this->last_sample_ms_ = now;
    this->sample_pin_(now);
  }

  this->check_timeout_(now);
}

void WeightedPulseMeter::sample_pin_(uint32_t now) {
  const bool s = this->pin_->digital_read();

  if (s != this->raw_state_) {
    this->raw_state_ = s;
    this->last_raw_change_ms_ = now;
  }

  // Debounce
  if ((now - this->last_raw_change_ms_) >= this->debounce_ms_ && (this->debounced_state_ != this->raw_state_)) {
    // A stable change has occurred
    this->debounced_state_ = this->raw_state_;
    this->handle_edge_(this->debounced_state_, now);
  }
}

void WeightedPulseMeter::handle_edge_(bool new_state, uint32_t now) {
  // Determine which edge this is: true=new_state means pressing (OFF->ON), false means releasing (ON->OFF).
  const bool is_press = new_state;

  // Time since last debounced edge
  uint32_t dt = now - this->last_debounced_change_ms_;
  this->last_debounced_change_ms_ = now;

  // First edge after boot: initialize timing and add volume so total stays correct,
  // but skip flow rate calc (no dt yet).
  if (!this->initialized_) {
    this->initialized_ = true;
    this->timed_out_zeroed_ = false;
    const float add0 = is_press ? this->on_press_l_ : this->on_release_l_;
    this->add_volume_(add0);
    return;
  }

  if (dt < 5) dt = 5;  // guard absurd dt from ISR jitter or clock wrap

  const float liters = is_press ? this->on_press_l_ : this->on_release_l_;
  const float inst_lpm = (liters * 60000.0f) / static_cast<float>(dt);

  // EMA smoothing
  if (!this->has_flow_) {
    this->flow_lpm_ = inst_lpm;
    this->has_flow_ = true;
  } else {
    this->flow_lpm_ = this->alpha_ * inst_lpm + (1.0f - this->alpha_) * this->flow_lpm_;
  }
  this->publish_flow_(this->flow_lpm_);

  this->timed_out_zeroed_ = false;
  this->add_volume_(liters);
}

void WeightedPulseMeter::check_timeout_(uint32_t now) {
  if (!this->initialized_) return;
  if (this->timed_out_zeroed_) return;

  if ((now - this->last_debounced_change_ms_) > this->timeout_ms_) {
    this->flow_lpm_ = 0.0f;
    this->publish_flow_(0.0f);
    this->timed_out_zeroed_ = true;
  }
}

void WeightedPulseMeter::publish_flow_(float lpm) {
  if (this->flow_sensor_ != nullptr) this->flow_sensor_->publish_state(lpm);
}

void WeightedPulseMeter::publish_total_() {
  if (this->total_sensor_ != nullptr) this->total_sensor_->publish_state(this->total_l_);
}

void WeightedPulseMeter::add_volume_(float liters) {
  this->total_l_ += liters;
  this->publish_total_();

  // Save total throttled to ~30s to limit flash wear
  static const uint32_t SAVE_PERIOD_MS = 30000U;
  static uint32_t last_save = 0;
  const uint32_t now = millis();
  if ((now - last_save) > SAVE_PERIOD_MS) {
    this->pref_total_.save(&this->total_l_);
    last_save = now;
  }
}

void WeightedPulseMeter::set_total(float liters) {
  this->total_l_ = liters;
  this->publish_total_();
  this->pref_total_.save(&this->total_l_);
}

void WeightedPulseMeter::set_weights(float on_press_l, float on_release_l) {
  this->on_press_l_ = on_press_l;
  this->on_release_l_ = on_release_l;
}

}  // namespace weighted_pulse_meter
}  // namespace esphome
