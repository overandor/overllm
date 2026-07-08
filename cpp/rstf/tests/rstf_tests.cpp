#include "overllm/rstf.hpp"

#include <cassert>
#include <cmath>
#include <iostream>
#include <string>

namespace {

bool approx_zero(double value) {
  return std::fabs(value) < 1e-12;
}

}  // namespace

int main() {
  using overllm::rstf::Options;
  using overllm::rstf::canonicalize;
  using overllm::rstf::compute_fingerprint;
  using overllm::rstf::utf8_byte_length;

  assert(utf8_byte_length("test") == 4);
  assert(utf8_byte_length("ʇsǝʇ") == std::string("ʇsǝʇ").size());

  const auto upside = compute_fingerprint("ʇsǝʇ");
  assert(upside.canonical_text == "test");
  assert(upside.raw_utf8_bytes > upside.canonical_utf8_bytes);
  assert(upside.bytes_saved > 0);
  assert(upside.byte_savings_ratio > 0.0);

  const auto homoglyph = compute_fingerprint("раураl");  // Cyrillic r/a/u/r/a + Latin l.
  assert(homoglyph.canonical_text == "paypal");
  assert(homoglyph.bytes_saved > 0);

  const auto bidi = compute_fingerprint(std::string("safe") + "\xE2\x80\xAE" + "text");
  assert(bidi.canonical_text == "safetext");
  assert(bidi.bytes_saved == 3);

  const auto plain = compute_fingerprint("tset");
  assert(plain.canonical_text == "tset");
  assert(plain.bytes_saved == 0);
  assert(approx_zero(plain.byte_savings_ratio));

  Options force_reverse;
  force_reverse.force_reverse = true;
  const auto reversed = compute_fingerprint("tset", force_reverse);
  assert(reversed.canonical_text == "test");
  assert(reversed.bytes_saved == 0);

  const auto json = overllm::rstf::to_json(upside);
  assert(json.find("canonical_text") != std::string::npos);
  assert(json.find("byte_savings_ratio") != std::string::npos);

  std::cout << "overllm-rstf-tests passed\n";
  return 0;
}
