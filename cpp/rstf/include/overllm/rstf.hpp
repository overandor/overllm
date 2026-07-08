#pragma once

#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace overllm::rstf {

struct Options {
  // Plain reversal is not safely inferable from bytes alone. Leave this false
  // unless a caller has an external transform receipt or explicit policy.
  bool force_reverse = false;
};

struct Fingerprint {
  std::string raw_text;
  std::string canonical_text;
  std::vector<std::string> transforms;
  std::size_t raw_utf8_bytes = 0;
  std::size_t canonical_utf8_bytes = 0;
  long long bytes_saved = 0;
  double byte_savings_ratio = 0.0;
  bool changed = false;
};

std::size_t utf8_byte_length(std::string_view text) noexcept;

std::string canonicalize(std::string_view text, Options options = {});

Fingerprint compute_fingerprint(std::string_view text, Options options = {});

std::string to_json(const Fingerprint& fingerprint);

}  // namespace overllm::rstf
