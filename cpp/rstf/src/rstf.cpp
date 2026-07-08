#include "overllm/rstf.hpp"

#include <algorithm>
#include <iomanip>
#include <sstream>
#include <unordered_map>

namespace overllm::rstf {
namespace {

using Codepoints = std::vector<char32_t>;

Codepoints decode_utf8(std::string_view input) {
  Codepoints out;
  for (std::size_t i = 0; i < input.size();) {
    const unsigned char c = static_cast<unsigned char>(input[i]);
    if (c < 0x80) {
      out.push_back(c);
      ++i;
    } else if ((c >> 5) == 0x6 && i + 1 < input.size()) {
      const char32_t cp = ((c & 0x1F) << 6) |
                          (static_cast<unsigned char>(input[i + 1]) & 0x3F);
      out.push_back(cp);
      i += 2;
    } else if ((c >> 4) == 0xE && i + 2 < input.size()) {
      const char32_t cp = ((c & 0x0F) << 12) |
                          ((static_cast<unsigned char>(input[i + 1]) & 0x3F) << 6) |
                          (static_cast<unsigned char>(input[i + 2]) & 0x3F);
      out.push_back(cp);
      i += 3;
    } else if ((c >> 3) == 0x1E && i + 3 < input.size()) {
      const char32_t cp = ((c & 0x07) << 18) |
                          ((static_cast<unsigned char>(input[i + 1]) & 0x3F) << 12) |
                          ((static_cast<unsigned char>(input[i + 2]) & 0x3F) << 6) |
                          (static_cast<unsigned char>(input[i + 3]) & 0x3F);
      out.push_back(cp);
      i += 4;
    } else {
      // Preserve malformed bytes as standalone codepoints. This keeps the
      // package deterministic without silently dropping data.
      out.push_back(c);
      ++i;
    }
  }
  return out;
}

std::string encode_utf8(const Codepoints& input) {
  std::string out;
  for (char32_t cp : input) {
    if (cp <= 0x7F) {
      out.push_back(static_cast<char>(cp));
    } else if (cp <= 0x7FF) {
      out.push_back(static_cast<char>(0xC0 | ((cp >> 6) & 0x1F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else if (cp <= 0xFFFF) {
      out.push_back(static_cast<char>(0xE0 | ((cp >> 12) & 0x0F)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    } else {
      out.push_back(static_cast<char>(0xF0 | ((cp >> 18) & 0x07)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3F)));
      out.push_back(static_cast<char>(0x80 | (cp & 0x3F)));
    }
  }
  return out;
}

bool is_bidi_control(char32_t cp) {
  return (cp >= 0x202A && cp <= 0x202E) || (cp >= 0x2066 && cp <= 0x2069);
}

const std::unordered_map<char32_t, char32_t>& upside_down_map() {
  static const std::unordered_map<char32_t, char32_t> map = {
      // Only non-ASCII rotated glyphs are included here. ASCII characters such
      // as s, o, x, z, l, H, I, N, O, S and X may appear unchanged in an
      // upside-down rendering, but treating them as transform evidence would
      // create false positives on clean text.
      {U'ɐ', U'a'}, {U'ɑ', U'a'}, {U'ᵇ', U'b'}, {U'ɔ', U'c'},
      {U'ǝ', U'e'}, {U'ɟ', U'f'}, {U'ƃ', U'g'}, {U'ɥ', U'h'},
      {U'ᴉ', U'i'}, {U'ı', U'i'}, {U'ɾ', U'j'}, {U'ʞ', U'k'},
      {U'ɯ', U'm'}, {U'ɹ', U'r'}, {U'ʇ', U't'}, {U'ʌ', U'v'},
      {U'ʍ', U'w'}, {U'ʎ', U'y'}, {U'∀', U'A'}, {U'ᗺ', U'B'},
      {U'Ɔ', U'C'}, {U'ᗡ', U'D'}, {U'Ǝ', U'E'}, {U'Ⅎ', U'F'},
      {U'⅁', U'G'}, {U'ſ', U'J'}, {U'Ʞ', U'K'}, {U'˥', U'L'},
      {U'Ԁ', U'P'}, {U'Ό', U'Q'}, {U'ᴚ', U'R'}, {U'⊥', U'T'},
      {U'∩', U'U'}, {U'Λ', U'V'}, {U'⅄', U'Y'}, {U'¡', U'!'},
      {U'¿', U'?'}, {U'˙', U'.'}, {U'ʻ', U','}
  };
  return map;
}

const std::unordered_map<char32_t, char32_t>& homoglyph_map() {
  static const std::unordered_map<char32_t, char32_t> map = {
      // Cyrillic uppercase confusables.
      {U'А', U'A'}, {U'В', U'B'}, {U'Е', U'E'}, {U'К', U'K'},
      {U'М', U'M'}, {U'Н', U'H'}, {U'О', U'O'}, {U'Р', U'P'},
      {U'С', U'C'}, {U'Т', U'T'}, {U'Х', U'X'}, {U'У', U'Y'},
      // Cyrillic lowercase confusables.
      {U'а', U'a'}, {U'е', U'e'}, {U'о', U'o'}, {U'р', U'p'},
      {U'с', U'c'}, {U'х', U'x'}, {U'у', U'y'}, {U'і', U'i'},
      {U'ј', U'j'}, {U'ӏ', U'l'},
      // Greek uppercase confusables.
      {U'Α', U'A'}, {U'Β', U'B'}, {U'Ε', U'E'}, {U'Ζ', U'Z'},
      {U'Η', U'H'}, {U'Ι', U'I'}, {U'Κ', U'K'}, {U'Μ', U'M'},
      {U'Ν', U'N'}, {U'Ο', U'O'}, {U'Ρ', U'P'}, {U'Τ', U'T'},
      {U'Χ', U'X'}, {U'Υ', U'Y'},
      // Greek lowercase confusables.
      {U'ο', U'o'}, {U'ρ', U'p'}, {U'ν', U'v'}, {U'χ', U'x'},
      {U'ι', U'i'}
  };
  return map;
}

std::string escape_json(std::string_view input) {
  std::ostringstream oss;
  for (unsigned char c : input) {
    switch (c) {
      case '"': oss << "\\\""; break;
      case '\\': oss << "\\\\"; break;
      case '\b': oss << "\\b"; break;
      case '\f': oss << "\\f"; break;
      case '\n': oss << "\\n"; break;
      case '\r': oss << "\\r"; break;
      case '\t': oss << "\\t"; break;
      default:
        if (c < 0x20) {
          oss << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c);
        } else {
          oss << static_cast<char>(c);
        }
    }
  }
  return oss.str();
}

}  // namespace

std::size_t utf8_byte_length(std::string_view text) noexcept {
  return text.size();
}

std::string canonicalize(std::string_view text, Options options) {
  return compute_fingerprint(text, options).canonical_text;
}

Fingerprint compute_fingerprint(std::string_view text, Options options) {
  Fingerprint fp;
  fp.raw_text = std::string(text);
  fp.raw_utf8_bytes = utf8_byte_length(text);

  Codepoints cps = decode_utf8(text);
  Codepoints normalized;
  normalized.reserve(cps.size());

  bool saw_bidi = false;
  bool saw_homoglyph = false;
  bool saw_upside = false;

  const auto& upside = upside_down_map();
  const auto& homoglyph = homoglyph_map();

  for (char32_t cp : cps) {
    if (is_bidi_control(cp)) {
      saw_bidi = true;
      continue;
    }

    auto up = upside.find(cp);
    if (up != upside.end()) {
      saw_upside = true;
      normalized.push_back(up->second);
      continue;
    }

    auto hg = homoglyph.find(cp);
    if (hg != homoglyph.end()) {
      saw_homoglyph = true;
      normalized.push_back(hg->second);
      continue;
    }

    normalized.push_back(cp);
  }

  if (saw_upside || options.force_reverse) {
    std::reverse(normalized.begin(), normalized.end());
  }

  if (saw_bidi) fp.transforms.push_back("bidi_override");
  if (saw_homoglyph) fp.transforms.push_back("homoglyph");
  if (saw_upside) fp.transforms.push_back("upside_down");
  if (options.force_reverse && !saw_upside) fp.transforms.push_back("reversed_forced");

  fp.canonical_text = encode_utf8(normalized);
  fp.canonical_utf8_bytes = utf8_byte_length(fp.canonical_text);
  fp.bytes_saved = static_cast<long long>(fp.raw_utf8_bytes) -
                   static_cast<long long>(fp.canonical_utf8_bytes);
  fp.byte_savings_ratio = fp.raw_utf8_bytes == 0
      ? 0.0
      : static_cast<double>(fp.bytes_saved) / static_cast<double>(fp.raw_utf8_bytes);
  fp.changed = fp.raw_text != fp.canonical_text || !fp.transforms.empty();
  return fp;
}

std::string to_json(const Fingerprint& fp) {
  std::ostringstream oss;
  oss << "{";
  oss << "\"raw_text\":\"" << escape_json(fp.raw_text) << "\",";
  oss << "\"canonical_text\":\"" << escape_json(fp.canonical_text) << "\",";
  oss << "\"raw_utf8_bytes\":" << fp.raw_utf8_bytes << ",";
  oss << "\"canonical_utf8_bytes\":" << fp.canonical_utf8_bytes << ",";
  oss << "\"bytes_saved\":" << fp.bytes_saved << ",";
  oss << "\"byte_savings_ratio\":" << fp.byte_savings_ratio << ",";
  oss << "\"changed\":" << (fp.changed ? "true" : "false") << ",";
  oss << "\"transforms\":[";
  for (std::size_t i = 0; i < fp.transforms.size(); ++i) {
    if (i) oss << ",";
    oss << "\"" << escape_json(fp.transforms[i]) << "\"";
  }
  oss << "]}";
  return oss.str();
}

}  // namespace overllm::rstf
