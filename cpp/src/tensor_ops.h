#pragma once
namespace overllm {
void matmul(const float* A, const float* B, float* C, int M, int N, int K);
void add_bias(float* dst, const float* bias, int M, int N);
void gelu(float* dst, const float* src, int n);
void layer_norm(float* dst, const float* src, const float* gamma, const float* beta, int rows, int cols, float eps);
void softmax(float* dst, const float* src, int rows, int cols);
void add(float* dst, const float* a, const float* b, int n);
void mul(float* dst, const float* a, const float* b, int n);
void copy(float* dst, const float* src, int n);
void fill(float* dst, float val, int n);
void zero(float* dst, int n);
float cross_entropy_loss(const float* logits, int vocab_size, int target_token, float* dlogits);
int argmax(const float* vec, int n);
int sample_temperature(const float* logits, int vocab_size, float temp, unsigned seed);
}
