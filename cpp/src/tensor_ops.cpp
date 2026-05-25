#include "tensor_ops.h"
#include <cmath>
#include <cstring>
#include <random>

namespace overllm {

void matmul(const float* A, const float* B, float* C, int M, int N, int K) {
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N; ++j) {
            float sum = 0.0f;
            for (int k = 0; k < K; ++k) sum += A[i*K+k] * B[k*N+j];
            C[i*N+j] = sum;
        }
    }
}

void add_bias(float* dst, const float* bias, int M, int N) {
    for (int i = 0; i < M; ++i) for (int j = 0; j < N; ++j) dst[i*N+j] += bias[j];
}

void gelu(float* dst, const float* src, int n) {
    const float c = 0.7978845608f;
    for (int i = 0; i < n; ++i) {
        float x = src[i];
        dst[i] = x * 0.5f * (1.0f + std::tanh(c * (x + 0.044715f * x*x*x)));
    }
}

void layer_norm(float* dst, const float* src, const float* gamma, const float* beta, int rows, int cols, float eps) {
    for (int i = 0; i < rows; ++i) {
        float mean = 0.0f;
        for (int j = 0; j < cols; ++j) mean += src[i*cols+j];
        mean /= cols;
        float var = 0.0f;
        for (int j = 0; j < cols; ++j) { float d = src[i*cols+j]-mean; var += d*d; }
        var /= cols;
        float inv = 1.0f / std::sqrt(var + eps);
        for (int j = 0; j < cols; ++j) dst[i*cols+j] = gamma[j] * (src[i*cols+j]-mean) * inv + beta[j];
    }
}

void softmax(float* dst, const float* src, int rows, int cols) {
    for (int i = 0; i < rows; ++i) {
        float maxv = src[i*cols];
        for (int j = 1; j < cols; ++j) if (src[i*cols+j] > maxv) maxv = src[i*cols+j];
        float sum = 0.0f;
        for (int j = 0; j < cols; ++j) { dst[i*cols+j] = std::exp(src[i*cols+j]-maxv); sum += dst[i*cols+j]; }
        for (int j = 0; j < cols; ++j) dst[i*cols+j] /= sum;
    }
}

void add(float* dst, const float* a, const float* b, int n) { for (int i=0;i<n;++i) dst[i]=a[i]+b[i]; }
void mul(float* dst, const float* a, const float* b, int n) { for (int i=0;i<n;++i) dst[i]=a[i]*b[i]; }
void copy(float* dst, const float* src, int n) { std::memcpy(dst, src, n*sizeof(float)); }
void fill(float* dst, float val, int n) { for (int i=0;i<n;++i) dst[i]=val; }
void zero(float* dst, int n) { std::memset(dst, 0, n*sizeof(float)); }

float cross_entropy_loss(const float* logits, int vocab_size, int target_token, float* dlogits) {
    float max_logit = logits[0];
    for (int i=1;i<vocab_size;++i) if (logits[i]>max_logit) max_logit=logits[i];
    float sum_exp = 0.0f;
    for (int i=0;i<vocab_size;++i) { dlogits[i]=std::exp(logits[i]-max_logit); sum_exp+=dlogits[i]; }
    for (int i=0;i<vocab_size;++i) dlogits[i]/=sum_exp;
    float loss = -std::log(dlogits[target_token]+1e-10f);
    dlogits[target_token] -= 1.0f;
    return loss;
}

int argmax(const float* vec, int n) { int idx=0; for(int i=1;i<n;++i) if(vec[i]>vec[idx]) idx=i; return idx; }

int sample_temperature(const float* logits, int vocab_size, float temp, unsigned seed) {
    std::vector<float> probs(vocab_size);
    float max_logit = logits[0];
    for (int i=1;i<vocab_size;++i) if (logits[i]>max_logit) max_logit=logits[i];
    float sum = 0.0f;
    for (int i=0;i<vocab_size;++i) { probs[i]=std::exp((logits[i]-max_logit)/temp); sum+=probs[i]; }
    std::mt19937 gen(seed);
    std::uniform_real_distribution<float> dist(0.0f, sum);
    float r = dist(gen), acc = 0.0f;
    for (int i=0;i<vocab_size;++i) { acc+=probs[i]; if(r<=acc) return i; }
    return vocab_size-1;
}

} // namespace overllm
