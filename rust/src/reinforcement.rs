use ndarray::{Array1, Array2, ArrayView1};
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::collections::VecDeque;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RLConfig {
    pub learning_rate: f64,
    pub gamma: f64,          // Discount factor
    pub epsilon: f64,        // Exploration rate
    pub epsilon_decay: f64,
    pub min_epsilon: f64,
    pub batch_size: usize,
    pub memory_size: usize,
    pub target_update_freq: usize,
}

impl Default for RLConfig {
    fn default() -> Self {
        RLConfig {
            learning_rate: 0.001,
            gamma: 0.99,
            epsilon: 0.1,
            epsilon_decay: 0.995,
            min_epsilon: 0.01,
            batch_size: 32,
            memory_size: 10000,
            target_update_freq: 100,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transition {
    pub state: Vec<f64>,
    pub action: usize,
    pub reward: f64,
    pub next_state: Vec<f64>,
    pub done: bool,
}

pub struct ReplayBuffer {
    buffer: VecDeque<Transition>,
    capacity: usize,
}

impl ReplayBuffer {
    pub fn new(capacity: usize) -> Self {
        ReplayBuffer {
            buffer: VecDeque::with_capacity(capacity),
            capacity,
        }
    }

    pub fn push(&mut self, transition: Transition) {
        if self.buffer.len() >= self.capacity {
            self.buffer.pop_front();
        }
        self.buffer.push_back(transition);
    }

    pub fn sample(&self, batch_size: usize) -> Vec<&Transition> {
        let mut rng = rand::thread_rng();
        let n = self.buffer.len().min(batch_size);
        let mut indices: Vec<usize> = (0..self.buffer.len()).collect();
        for i in 0..n {
            let j = rng.gen_range(i..self.buffer.len());
            indices.swap(i, j);
        }
        indices.iter().take(n).filter_map(|i| self.buffer.get(*i)).collect()
    }

    pub fn len(&self) -> usize {
        self.buffer.len()
    }
}

// Deep Q-Network (simplified - in production use a real neural network)
pub struct QNetwork {
    weights: Array2<f64>,
    biases: Array1<f64>,
    input_dim: usize,
    output_dim: usize,
}

impl QNetwork {
    pub fn new(input_dim: usize, output_dim: usize) -> Self {
        let mut rng = rand::thread_rng();
        let scale = (2.0 / (input_dim + output_dim) as f64).sqrt();
        
        let weights = Array2::from_shape_fn((input_dim, output_dim), |_| {
            (rng.gen::<f64>() - 0.5) * 2.0 * scale
        });
        
        let biases = Array1::zeros(output_dim);
        
        QNetwork {
            weights,
            biases,
            input_dim,
            output_dim,
        }
    }

    pub fn forward(&self, state: &ArrayView1<f64>) -> Array1<f64> {
        let q_values = state.dot(&self.weights) + &self.biases;
        q_values
    }

    pub fn update(&mut self, state: &ArrayView1<f64>, target_q: &ArrayView1<f64>, lr: f64) {
        let q_values = self.forward(state);
        let error = target_q - &q_values;
        
        // Gradient descent update (simplified)
        for i in 0..self.input_dim {
            for j in 0..self.output_dim {
                self.weights[[i, j]] += lr * error[j] * state[i];
            }
        }
        
        for j in 0..self.output_dim {
            self.biases[j] += lr * error[j];
        }
    }
}

// PPO-style Actor-Critic (simplified)
pub struct ActorCritic {
    actor: QNetwork,
    critic: QNetwork,
    config: RLConfig,
}

impl ActorCritic {
    pub fn new(state_dim: usize, action_dim: usize, config: RLConfig) -> Self {
        ActorCritic {
            actor: QNetwork::new(state_dim, action_dim),
            critic: QNetwork::new(state_dim, 1),
            config,
        }
    }

    pub fn select_action(&mut self, state: &[f64]) -> usize {
        let mut rng = rand::thread_rng();
        
        if rng.gen::<f64>() < self.config.epsilon {
            // Explore: random action
            rng.gen_range(0..self.actor.output_dim)
        } else {
            // Exploit: best action from actor
            let state_arr = Array1::from(state.to_vec());
            let q_values = self.actor.forward(&state_arr.view());
            q_values.iter().enumerate()
                .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
                .map(|(i, _)| i)
                .unwrap_or(0)
        }
    }

    pub fn update(&mut self, transition: &Transition) -> f64 {
        let state_arr = Array1::from(transition.state.clone());
        let next_state_arr = Array1::from(transition.next_state.clone());
        
        // Critic update
        let current_value = self.critic.forward(&state_arr.view())[0];
        let next_value = if transition.done {
            0.0
        } else {
            self.critic.forward(&next_state_arr.view())[0]
        };
        
        let td_target = transition.reward + self.config.gamma * next_value;
        let td_error = td_target - current_value;
        
        let target_critic = Array1::from(vec![td_target]);
        self.critic.update(&state_arr.view(), &target_critic.view(), self.config.learning_rate);
        
        // Actor update (policy gradient)
        let action_q = self.actor.forward(&state_arr.view());
        let mut target_actor = action_q.clone();
        target_actor[transition.action] += td_error;
        self.actor.update(&state_arr.view(), &target_actor.view(), self.config.learning_rate);
        
        // Decay epsilon
        self.config.epsilon = (self.config.epsilon * self.config.epsilon_decay).max(self.config.min_epsilon);
        
        td_error.abs()
    }
}

// Advantage Actor-Critic (A2C)
pub struct A2CAgent {
    actor_critic: ActorCritic,
    replay_buffer: ReplayBuffer,
    step_count: usize,
}

impl A2CAgent {
    pub fn new(state_dim: usize, action_dim: usize, config: RLConfig) -> Self {
        A2CAgent {
            actor_critic: ActorCritic::new(state_dim, action_dim, config.clone()),
            replay_buffer: ReplayBuffer::new(config.memory_size),
            step_count: 0,
        }
    }

    pub fn act(&mut self, state: &[f64]) -> usize {
        self.actor_critic.select_action(state)
    }

    pub fn step(&mut self, state: &[f64], action: usize, reward: f64, next_state: &[f64], done: bool) -> f64 {
        let transition = Transition {
            state: state.to_vec(),
            action,
            reward,
            next_state: next_state.to_vec(),
            done,
        };

        self.replay_buffer.push(transition.clone());
        self.step_count += 1;

        // Update immediately (A2C style)
        let td_error = self.actor_critic.update(&transition);
        
        td_error
    }

    pub fn train_batch(&mut self) -> f64 {
        if self.replay_buffer.len() < self.actor_critic.config.batch_size {
            return 0.0;
        }
        
        let batch: Vec<Transition> = self.replay_buffer.sample(self.actor_critic.config.batch_size)
            .into_iter()
            .cloned()
            .collect();
        let batch_len = batch.len();
        let mut total_loss = 0.0;
        
        for transition in batch {
            total_loss += self.actor_critic.update(&transition).abs();
        }
        
        total_loss / batch_len as f64
    }

    pub fn get_epsilon(&self) -> f64 {
        self.actor_critic.config.epsilon
    }

    pub fn save(&self, path: &str) -> Result<(), String> {
        // Save model weights (simplified)
        let data = serde_json::to_string(&self.actor_critic.config)
            .map_err(|e| format!("Failed to serialize config: {}", e))?;
        std::fs::write(path, data)
            .map_err(|e| format!("Failed to write to {}: {}", path, e))?;
        Ok(())
    }

    pub fn load(&mut self, path: &str) -> Result<(), String> {
        let data = std::fs::read_to_string(path)
            .map_err(|e| format!("Failed to read {}: {}", path, e))?;
        let config: RLConfig = serde_json::from_str(&data)
            .map_err(|e| format!("Failed to deserialize config: {}", e))?;
        self.actor_critic.config = config;
        Ok(())
    }
}

// Reward shaping for OverLLM
pub struct RewardShaper {
    pub base_reward: f64,
    pub context_bonus: f64,
    pub diversity_bonus: f64,
    pub novelty_bonus: f64,
}

impl RewardShaper {
    pub fn new() -> Self {
        RewardShaper {
            base_reward: 1.0,
            context_bonus: 0.5,
            diversity_bonus: 0.3,
            novelty_bonus: 0.2,
        }
    }

    pub fn compute_reward(
        &self,
        response_quality: f64,
        context_relevance: f64,
        diversity_score: f64,
        novelty_score: f64,
    ) -> f64 {
        self.base_reward * response_quality
            + self.context_bonus * context_relevance
            + self.diversity_bonus * diversity_score
            + self.novelty_bonus * novelty_score
    }

    pub fn compute_dpo_reward(&self, chosen_logp: f64, rejected_logp: f64) -> f64 {
        // Reward based on margin between chosen and rejected
        let margin = chosen_logp - rejected_logp;
        1.0 / (1.0 + (-margin).exp()) // Sigmoid of margin
    }
}

// RL training loop for OverLLM
pub struct RLTrainer {
    agent: A2CAgent,
    reward_shaper: RewardShaper,
    state_dim: usize,
    action_dim: usize,
}

impl RLTrainer {
    pub fn new(state_dim: usize, action_dim: usize) -> Self {
        let config = RLConfig::default();
        RLTrainer {
            agent: A2CAgent::new(state_dim, action_dim, config),
            reward_shaper: RewardShaper::new(),
            state_dim,
            action_dim,
        }
    }

    pub fn train_episode(&mut self, max_steps: usize) -> (f64, usize) {
        let mut total_reward = 0.0;
        let mut state = vec![0.0; self.state_dim];
        
        for step in 0..max_steps {
            let action = self.agent.act(&state);
            
            // Simulate environment (in production, this calls OverLLM)
            let (next_state, reward, done) = self.step_environment(&state, action);
            
            let td_error = self.agent.step(&state, action, reward, &next_state, done);
            total_reward += reward;
            
            state = next_state;
            
            if done {
                break;
            }
        }
        
        (total_reward, max_steps)
    }

    fn step_environment(&self, state: &[f64], action: usize) -> (Vec<f64>, f64, bool) {
        // Simulated environment step
        // In production, this would:
        // 1. Generate response using OverLLM
        // 2. Evaluate response quality
        // 3. Compute reward using RewardShaper
        
        let mut next_state = state.to_vec();
        next_state[action % self.state_dim] += 0.1;
        
        let reward = self.reward_shaper.compute_reward(0.8, 0.7, 0.6, 0.5);
        let done = rand::random::<f64>() < 0.1; // 10% chance of episode end
        
        (next_state, reward, done)
    }

    pub fn train(&mut self, num_episodes: usize) -> Vec<f64> {
        let mut episode_rewards = Vec::new();
        
        for episode in 0..num_episodes {
            let (reward, steps) = self.train_episode(100);
            episode_rewards.push(reward);
            
            // Batch training
            let loss = self.agent.train_batch();
            
            if episode % 10 == 0 {
                println!("Episode {}: reward={:.2}, steps={}, loss={:.4}, epsilon={:.3}",
                    episode, reward, steps, loss, self.agent.get_epsilon());
            }
        }
        
        episode_rewards
    }
}
