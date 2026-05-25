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

void matmul_backward(const float* A, const float* B, const float* dC, float* dA, float* dB, int M, int N, int K) {
    // Safety: zero out gradients first
    if (dA) std::fill(dA, dA + M*K, 0.0f);
    if (dB) std::fill(dB, dB + K*N, 0.0f);
    
    // dA = dC * B^T
    if (dA && A && B && dC) {
        for (int i = 0; i < M; ++i) {
            for (int k = 0; k < K; ++k) {
                float sum = 0.0f;
                for (int j = 0; j < N; ++j) {
                    if (i*N+j < M*N && k*N+j < K*N) {
                        sum += dC[i*N+j] * B[k*N+j];
                    }
                }
                if (i*K+k < M*K) dA[i*K+k] = sum;
            }
        }
    }
    // dB = A^T * dC
    if (dB && A && B && dC) {
        for (int k = 0; k < K; ++k) {
            for (int j = 0; j < N; ++j) {
                float sum = 0.0f;
                for (int i = 0; i < M; ++i) {
                    if (i*K+k < M*K && i*N+j < M*N) {
                        sum += A[i*K+k] * dC[i*N+j];
                    }
                }
                if (k*N+j < K*N) dB[k*N+j] = sum;
            }
        }
    }
}

void add_bias_backward(const float* dbias, float* ddst, int M, int N) {
    if (!dbias || !ddst) return;
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N; ++j) {
            if (i*N+j < M*N && j < N) {
                ddst[i*N+j] += dbias[j];
            }
        }
    }
}

void gelu_backward(const float* dst, const float* src, const float* ddst, float* dsrc, int n) {
    if (!dst || !src || !ddst || !dsrc) return;
    const float c = 0.7978845608f;
    for (int i = 0; i < n; ++i) {
        if (i >= n) break;
        float x = src[i];
        float tanh_arg = c * (x + 0.044715f * x*x*x);
        float sech = 1.0f / std::cosh(tanh_arg);
        float gelu_grad = 0.5f * (1.0f + std::tanh(tanh_arg)) + x * 0.5f * sech * sech * c * (1.0f + 0.134145f * x*x);
        dsrc[i] = ddst[i] * gelu_grad;
    }
}

void layer_norm_backward(const float* src, const float* gamma, const float* beta, const float* ddst, float* dsrc, float* dgamma, float* dbeta, int rows, int cols, float eps) {
    if (!src || !gamma || !beta || !ddst || !dsrc || !dgamma || !dbeta) return;
    
    // Zero out dgamma and dbeta first
    std::fill(dgamma, dgamma + cols, 0.0f);
    std::fill(dbeta, dbeta + cols, 0.0f);
    
    for (int i = 0; i < rows; ++i) {
        if (i >= rows) break;
        float mean = 0.0f;
        for (int j = 0; j < cols; ++j) {
            if (i*cols+j < rows*cols) mean += src[i*cols+j];
        }
        mean /= cols;
        float var = 0.0f;
        for (int j = 0; j < cols; ++j) {
            if (i*cols+j < rows*cols) {
                float d = src[i*cols+j]-mean;
                var += d*d;
            }
        }
        var /= cols;
        float inv = 1.0f / std::sqrt(var + eps);
        float inv3 = inv * inv * inv;
        
        // dgamma and dbeta
        for (int j = 0; j < cols; ++j) {
            if (j < cols && i*cols+j < rows*cols) {
                dgamma[j] += ddst[i*cols+j] * (src[i*cols+j] - mean) * inv;
                dbeta[j] += ddst[i*cols+j];
            }
        }
        
        // dsrc
        float dmean = 0.0f, dvar = 0.0f;
        for (int j = 0; j < cols; ++j) {
            if (j < cols && i*cols+j < rows*cols) {
                dmean += -gamma[j] * ddst[i*cols+j] * inv;
                dvar += -0.5f * gamma[j] * ddst[i*cols+j] * (src[i*cols+j] - mean) * inv3;
            }
        }
        for (int j = 0; j < cols; ++j) {
            if (i*cols+j < rows*cols) {
                dsrc[i*cols+j] = gamma[j] * ddst[i*cols+j] * inv + dvar * 2.0f * (src[i*cols+j] - mean) / cols + dmean / cols;
            }
        }
    }
}

void softmax_backward(const float* dst, const float* ddst, float* dsrc, int rows, int cols) {
    if (!dst || !ddst || !dsrc) return;
    for (int i = 0; i < rows; ++i) {
        if (i >= rows) break;
        float sum = 0.0f;
        for (int j = 0; j < cols; ++j) {
            if (i*cols+j < rows*cols) sum += dst[i*cols+j] * ddst[i*cols+j];
        }
        for (int j = 0; j < cols; ++j) {
            if (i*cols+j < rows*cols) {
                dsrc[i*cols+j] = dst[i*cols+j] * (ddst[i*cols+j] - sum);
            }
        }
    }
}

} // namespace overllm
