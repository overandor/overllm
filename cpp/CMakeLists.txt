cmake_minimum_required(VERSION 3.16)
project(overllm_cpp LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(APPLE)
    set(CMAKE_OSX_ARCHITECTURES "arm64")
endif()
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -ffast-math")
include_directories(${CMAKE_SOURCE_DIR}/include)
set(SOURCES src/tensor_ops.cpp src/model.cpp src/genetic_algorithm.cpp src/token_optimizer.cpp src/rl_trainer.cpp src/tokenizer.cpp src/llm_client.cpp)
add_library(overllm SHARED ${SOURCES})
set_target_properties(overllm PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../lib)
add_executable(overllm_inference src/inference_main.cpp ${SOURCES})
add_executable(test_overllm test_overllm.cpp ${SOURCES})
add_executable(train_online train_online.cpp ${SOURCES})
add_executable(test_llm_client test_llm_client.cpp ${SOURCES})

# Standalone BPE tokenizer CLI. Deliberately links only against
# src/tokenizer.cpp, not the full SOURCES list, so it builds independently
# of the other engine components (model/tensor_ops/rl_trainer/etc). This is
# the compiled artifact tools/bpe_parity_check.py runs to verify the C++
# tokenizer produces identical token IDs to the Python reference
# implementation (tools/bpe_tokenizer.py) on the same trained vocabulary.
add_executable(bpe_cli tools/bpe_cli.cpp src/tokenizer.cpp)

# Real transformer training experiment: next-token cross-entropy training
# on real tokenized text, reporting a per-epoch loss curve. Verifies the
# forward/backward/AdamW implementation in src/model.cpp actually performs
# gradient descent (loss decreases), unlike train_online.cpp's DPO loop,
# which trains on uniformly random token pairs with no learnable signal.
# Links only model.cpp + tensor_ops.cpp + tokenizer.cpp, independent of the
# other engine components.
add_executable(train_language_model tools/train_language_model.cpp src/model.cpp src/tensor_ops.cpp src/tokenizer.cpp)

# Numerical gradient check: verifies backward_impl_seq's analytical
# gradients against finite-difference estimates for a probed set of
# parameters (attention Q/K/V weights/biases, output projection at a
# non-last position, FFN, layer norms, embeddings). This is the actual
# correctness proof for the backward pass - see
# docs/TRANSFORMER_LEARNING.md for the bugs it verifies are fixed. Needs
# direct access to Model/TransformerBlock internals (model_internal.h) and
# tensor_ops.h, both in src/, not the public include/ directory other tools
# use, hence the extra include path.
add_executable(gradient_check tools/gradient_check.cpp src/model.cpp src/tensor_ops.cpp)
target_include_directories(gradient_check PRIVATE ${CMAKE_SOURCE_DIR}/src)
# -ffast-math permits float reassociation that adds noise to a
# finite-difference comparison; override the project-wide flag (set at
# line 8) for this one target so the check isn't fighting compiler-induced
# precision loss on top of legitimate float32 error. The trailing flag
# wins for GCC/Clang, so appending -fno-fast-math after the inherited
# flags is sufficient - no need to strip -ffast-math itself.
target_compile_options(gradient_check PRIVATE -fno-fast-math)
