#include "overllm/rstf.hpp"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::string read_stdin() {
  std::ostringstream ss;
  ss << std::cin.rdbuf();
  return ss.str();
}

std::string join_args(int start, int argc, char** argv) {
  std::ostringstream ss;
  for (int i = start; i < argc; ++i) {
    if (i > start) ss << ' ';
    ss << argv[i];
  }
  return ss.str();
}

void usage() {
  std::cerr << "Usage: overllm-rstf [--json] [--reverse] [text...]\n"
            << "\n"
            << "Canonicalizes RSTF-style transformed text before tokenizer/model execution.\n"
            << "If no text is provided, reads from stdin.\n";
}

}  // namespace

int main(int argc, char** argv) {
  bool json = false;
  overllm::rstf::Options options;
  int first_text_arg = 1;

  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--json") {
      json = true;
      first_text_arg = i + 1;
    } else if (arg == "--reverse") {
      options.force_reverse = true;
      first_text_arg = i + 1;
    } else if (arg == "--help" || arg == "-h") {
      usage();
      return 0;
    } else {
      first_text_arg = i;
      break;
    }
  }

  std::string input = first_text_arg < argc ? join_args(first_text_arg, argc, argv) : read_stdin();
  const auto fp = overllm::rstf::compute_fingerprint(input, options);

  if (json) {
    std::cout << overllm::rstf::to_json(fp) << "\n";
  } else {
    std::cout << fp.canonical_text;
    if (!fp.canonical_text.empty() && fp.canonical_text.back() != '\n') {
      std::cout << "\n";
    }
  }

  return 0;
}
