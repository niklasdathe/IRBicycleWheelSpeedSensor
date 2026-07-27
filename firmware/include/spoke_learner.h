#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

#include "ir_spoke_generated.h"

namespace ir_spoke {

struct SpokeEstimate {
  std::uint8_t spoke_count = 0;
  float confidence = 0.0f;
  float revolution_period_us = 0.0f;
  float wheel_hz = 0.0f;
  std::uint8_t current_spoke = 0;
  bool count_locked = false;
};

// Online interval-pattern matcher. No manual calibration and no heap use.
// Count inference requires a repeatable non-uniformity fingerprint. A perfectly
// uniform spoke pattern is mathematically ambiguous; confidence stays low.
class SpokeLearner {
 public:
  static constexpr std::size_t kHistory = 2 * generated::kSpokeCountMax + 8;

  bool ingest(std::uint64_t edge_us) {
    if (last_edge_us_ == 0) {
      last_edge_us_ = edge_us;
      return false;
    }
    const float interval = static_cast<float>(edge_us - last_edge_us_);
    last_edge_us_ = edge_us;
    if (interval < generated::kMinimumBlockedUs ||
        interval > static_cast<float>(generated::kLinkLossTimeoutUs)) {
      return false;
    }
    history_[history_head_] = interval;
    history_head_ = (history_head_ + 1) % kHistory;
    history_size_ = std::min(history_size_ + 1, kHistory);
    ++accepted_events_;

    if (!estimate_.count_locked &&
        accepted_events_ >= generated::kSpokeCountConfidenceEvents) {
      infer_count();
    }
    if (estimate_.count_locked) update_map(interval);
    return true;
  }

  const SpokeEstimate& estimate() const { return estimate_; }
  const std::array<float, generated::kSpokeCountMax>& interval_lut() const {
    return interval_lut_;
  }

 private:
  float history_back(std::size_t back) const {
    const std::size_t index =
        (history_head_ + kHistory - 1 - back) % kHistory;
    return history_[index];
  }

  void infer_count() {
    float best = std::numeric_limits<float>::infinity();
    float second = std::numeric_limits<float>::infinity();
    std::uint8_t best_count = 0;
    for (std::uint8_t n = generated::kSpokeCountMin;
         n <= generated::kSpokeCountMax; ++n) {
      if (history_size_ < 2U * n) continue;
      float error = 0.0f;
      float mean = 0.0f;
      for (std::uint8_t i = 0; i < n; ++i) {
        const float a = history_back(i);
        const float b = history_back(i + n);
        mean += 0.5f * (a + b);
        error += std::abs(a - b);
      }
      error /= std::max(mean, 1.0f);
      // Prefer the fundamental over a harmonic when scores are nearly equal.
      error *= 1.0f + 0.001f * n;
      if (error < best) {
        second = best;
        best = error;
        best_count = n;
      } else if (error < second) {
        second = error;
      }
    }
    const float separation =
        std::isfinite(second) ? (second - best) / std::max(second, 1e-6f) : 0.0f;
    estimate_.confidence = std::clamp(separation, 0.0f, 1.0f);
    // Require both low cycle-to-cycle error and separation from alternatives.
    if (best_count && best < 0.035f && estimate_.confidence > 0.08f) {
      estimate_.spoke_count = best_count;
      estimate_.count_locked = true;
      for (std::uint8_t i = 0; i < best_count; ++i) {
        interval_lut_[best_count - 1 - i] = history_back(i);
      }
      spoke_index_ = 0;
    }
  }

  void update_map(float interval) {
    const auto n = estimate_.spoke_count;
    auto& cell = interval_lut_[spoke_index_];
    const float previous = cell > 0.0f ? cell : interval;
    const float residual = std::abs(interval - previous);
    const float gate = std::max(80.0f, generated::kOutlierSigma * 0.08f * previous);
    if (residual <= gate) {
      cell += generated::kLearningRate * (interval - cell);
    }
    spoke_index_ = static_cast<std::uint8_t>((spoke_index_ + 1) % n);
    estimate_.current_spoke = spoke_index_;
    float revolution = 0.0f;
    for (std::uint8_t i = 0; i < n; ++i) revolution += interval_lut_[i];
    estimate_.revolution_period_us = revolution;
    estimate_.wheel_hz = revolution > 0.0f ? 1.0e6f / revolution : 0.0f;
  }

  std::array<float, kHistory> history_{};
  std::array<float, generated::kSpokeCountMax> interval_lut_{};
  std::size_t history_head_ = 0;
  std::size_t history_size_ = 0;
  std::uint64_t last_edge_us_ = 0;
  std::uint32_t accepted_events_ = 0;
  std::uint8_t spoke_index_ = 0;
  SpokeEstimate estimate_{};
};

}  // namespace ir_spoke
