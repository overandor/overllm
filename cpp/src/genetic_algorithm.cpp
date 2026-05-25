#include "overllm.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <random>
#include <fstream>

namespace overllm {

struct Genome {
    std::vector<float> weights;
    float fitness;
    int generation;
    
    Genome() : fitness(0.0f), generation(0) {}
    Genome(const std::vector<float>& w, float f = 0.0f, int gen = 0) 
        : weights(w), fitness(f), generation(gen) {}
};

struct GeneticAlgorithm {
    std::vector<Genome> population;
    int population_size;
    float mutation_rate;
    float crossover_rate;
    int genome_length;
    int generation;
    float elitism_rate;
    
    GeneticAlgorithm(int pop_size = 50, float mut_rate = 0.01f, 
                     float cross_rate = 0.7f, int genome_len = 1000)
        : population_size(pop_size), mutation_rate(mut_rate), 
          crossover_rate(cross_rate), genome_length(genome_len),
          generation(0), elitism_rate(0.1f) {
        initialize_population();
    }
    
    void initialize_population() {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::normal_distribution<float> dist(0.0f, 0.1f);
        
        population.clear();
        for (int i = 0; i < population_size; ++i) {
            std::vector<float> weights(genome_length);
            for (auto& w : weights) {
                w = dist(gen);
            }
            population.emplace_back(weights, 0.0f, 0);
        }
    }
    
    Genome tournament_selection(int tournament_size = 3) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<int> dist(0, population_size - 1);
        
        Genome best = population[dist(gen)];
        for (int i = 1; i < tournament_size; ++i) {
            Genome contender = population[dist(gen)];
            if (contender.fitness > best.fitness) {
                best = contender;
            }
        }
        return best;
    }
    
    Genome crossover(const Genome& parent1, const Genome& parent2) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_real_distribution<float> dist(0.0f, 1.0f);
        
        std::vector<float> child_weights(genome_length);
        
        if (dist(gen) < crossover_rate) {
            // Uniform crossover
            for (int i = 0; i < genome_length; ++i) {
                child_weights[i] = (dist(gen) < 0.5f) ? parent1.weights[i] : parent2.weights[i];
            }
        } else {
            // Clone one parent
            child_weights = (dist(gen) < 0.5f) ? parent1.weights : parent2.weights;
        }
        
        return Genome(child_weights, 0.0f, generation + 1);
    }
    
    void mutate(Genome& genome) {
        std::random_device rd;
        std::mt19937 gen(rd());
        std::normal_distribution<float> noise_dist(0.0f, 0.05f);
        std::uniform_real_distribution<float> prob_dist(0.0f, 1.0f);
        
        for (auto& weight : genome.weights) {
            if (prob_dist(gen) < mutation_rate) {
                weight += noise_dist(gen);
                // Clamp weights
                weight = std::max(-2.0f, std::min(2.0f, weight));
            }
        }
    }
    
    void evolve() {
        // Sort by fitness (descending)
        std::sort(population.begin(), population.end(), 
            [](const Genome& a, const Genome& b) { return a.fitness > b.fitness; });
        
        std::vector<Genome> new_population;
        
        // Elitism: keep top performers
        int elite_count = static_cast<int>(population_size * elitism_rate);
        for (int i = 0; i < elite_count; ++i) {
            new_population.push_back(population[i]);
        }
        
        // Generate offspring
        while (new_population.size() < population_size) {
            Genome parent1 = tournament_selection();
            Genome parent2 = tournament_selection();
            Genome child = crossover(parent1, parent2);
            mutate(child);
            new_population.push_back(child);
        }
        
        population = new_population;
        generation++;
    }
    
    Genome get_best_genome() const {
        if (population.empty()) return Genome();
        
        Genome best = population[0];
        for (const auto& genome : population) {
            if (genome.fitness > best.fitness) {
                best = genome;
            }
        }
        return best;
    }
    
    float get_average_fitness() const {
        if (population.empty()) return 0.0f;
        
        float sum = 0.0f;
        for (const auto& genome : population) {
            sum += genome.fitness;
        }
        return sum / population.size();
    }
    
    void evaluate_fitness(OverLLMModel* model, const std::vector<std::vector<int>>& test_sequences,
                         const std::vector<int>& correct_tokens) {
        for (size_t i = 0; i < population.size() && i < test_sequences.size(); ++i) {
            // Apply genome weights to model (simplified - just modify output layer)
            // In production, this would be more sophisticated
            float accuracy = 0.0f;
            int correct = 0;
            
            for (size_t j = 0; j < test_sequences.size(); ++j) {
                std::vector<float> logits(32000); // vocab size
                overllm_forward(model, test_sequences[j].data(), 
                               test_sequences[j].size(), logits.data());
                
                int predicted = overllm_sample_argmax(logits.data(), 32000);
                if (predicted == correct_tokens[j]) {
                    correct++;
                }
            }
            
            accuracy = static_cast<float>(correct) / test_sequences.size();
            population[i].fitness = accuracy;
        }
    }
    
    void save_generation(const std::string& path) {
        std::ofstream f(path, std::ios::binary);
        if (!f.is_open()) return;
        
        f.write(reinterpret_cast<const char*>(&generation), sizeof(int));
        f.write(reinterpret_cast<const char*>(&population_size), sizeof(int));
        
        for (const auto& genome : population) {
            f.write(reinterpret_cast<const char*>(&genome.fitness), sizeof(float));
            f.write(reinterpret_cast<const char*>(&genome.generation), sizeof(int));
            f.write(reinterpret_cast<const char*>(genome.weights.data()), 
                   genome.weights.size() * sizeof(float));
        }
        
        f.close();
    }
    
    void load_generation(const std::string& path) {
        std::ifstream f(path, std::ios::binary);
        if (!f.is_open()) return;
        
        f.read(reinterpret_cast<char*>(&generation), sizeof(int));
        f.read(reinterpret_cast<char*>(&population_size), sizeof(int));
        
        population.clear();
        for (int i = 0; i < population_size; ++i) {
            Genome genome;
            genome.weights.resize(genome_length);
            f.read(reinterpret_cast<char*>(&genome.fitness), sizeof(float));
            f.read(reinterpret_cast<char*>(&genome.generation), sizeof(int));
            f.read(reinterpret_cast<char*>(genome.weights.data()), 
                   genome.weights.size() * sizeof(float));
            population.push_back(genome);
        }
        
        f.close();
    }
};

} // namespace overllm
