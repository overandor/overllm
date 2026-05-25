use async_openai::{
    config::OpenAIConfig,
    types::{
        ChatCompletionRequestMessage, ChatCompletionRequestSystemMessageArgs,
        ChatCompletionRequestUserMessageArgs, CreateChatCompletionRequestArgs,
    },
    Client,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use tokio::sync::RwLock;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetaLLMTask {
    pub id: String,
    pub task_type: TaskType,
    pub description: String,
    pub context: String,
    pub status: TaskStatus,
    pub result: Option<String>,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskType {
    OptimizeModel,
    AddFeature,
    FixBug,
    GenerateCode,
    AnalyzeData,
    ImproveTraining,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskStatus {
    Pending,
    InProgress,
    Completed,
    Failed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeSuggestion {
    pub file_path: String,
    pub old_code: String,
    pub new_code: String,
    pub explanation: String,
    pub confidence: f64,
}

pub struct MetaLLMOrchestrator {
    client: Client<OpenAIConfig>,
    model: String,
    task_queue: RwLock<Vec<MetaLLMTask>>,
    code_history: RwLock<Vec<CodeSuggestion>>,
    overllm_state: RwLock<HashMap<String, String>>,
}

impl MetaLLMOrchestrator {
    pub fn new(api_key: String, model: String) -> Self {
        let client = Client::new();

        MetaLLMOrchestrator {
            client,
            model,
            task_queue: RwLock::new(Vec::new()),
            code_history: RwLock::new(Vec::new()),
            overllm_state: RwLock::new(HashMap::new()),
        }
    }

    pub async fn add_task(&self, task: MetaLLMTask) {
        let mut queue = self.task_queue.write().await;
        queue.push(task);
    }

    pub async fn process_tasks(&self) -> Result<usize, String> {
        let mut queue = self.task_queue.write().await;
        let mut processed = 0;
        
        let tasks: Vec<_> = queue.drain(..).collect();
        drop(queue);
        
        for task in tasks {
            let result = match task.task_type {
                TaskType::OptimizeModel => self.optimize_model(&task).await,
                TaskType::AddFeature => self.add_feature(&task).await,
                TaskType::FixBug => self.fix_bug(&task).await,
                TaskType::GenerateCode => self.generate_code(&task).await,
                TaskType::AnalyzeData => self.analyze_data(&task).await,
                TaskType::ImproveTraining => self.improve_training(&task).await,
            };
            
            match result {
                Ok(output) => {
                    processed += 1;
                    self.record_code_suggestion(&task, &output).await;
                }
                Err(e) => eprintln!("Task failed: {}", e),
            }
        }
        
        Ok(processed)
    }

    async fn optimize_model(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are an expert ML engineer specializing in transformer models and LLM optimization.
Your task is to analyze the current OverLLM model architecture and suggest optimizations.
Focus on: memory efficiency, inference speed, training stability, and model capacity.
Provide concrete code changes with explanations."#;

        let user_prompt = format!(
            "Current model state:\n{}\n\nTask: {}\n\nContext: {}",
            self.get_model_state().await,
            task.description,
            task.context
        );

        let response = self
            .chat_completion(system_prompt, &user_prompt)
            .await?;

        Ok(response)
    }

    async fn add_feature(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are a senior systems architect for OverLLM.
Your task is to design and implement new features for the OverLLM system.
The system is built in C++ (inference), Go (orchestration), and Rust (telemetry).
Provide complete, compilable code with proper error handling."#;

        let user_prompt = format!(
            "Feature request: {}\n\nContext: {}\n\nCurrent architecture:\n{}",
            task.description,
            task.context,
            self.get_architecture_overview().await
        );

        let response = self.chat_completion(system_prompt, &user_prompt).await?;
        Ok(response)
    }

    async fn fix_bug(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are a debugging expert for the OverLLM system.
Analyze the reported bug, identify the root cause, and provide a fix.
The system spans C++, Go, and Rust components."#;

        let user_prompt = format!(
            "Bug report: {}\n\nContext: {}\n\nRelevant code:\n{}",
            task.description,
            task.context,
            self.get_relevant_code(&task.context).await
        );

        let response = self.chat_completion(system_prompt, &user_prompt).await?;
        Ok(response)
    }

    async fn generate_code(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are a code generation specialist for OverLLM.
Generate clean, efficient, and well-documented code in the specified language.
Follow the existing code style and conventions."#;

        let user_prompt = format!(
            "Code generation request: {}\n\nContext: {}",
            task.description, task.context
        );

        let response = self.chat_completion(system_prompt, &user_prompt).await?;
        Ok(response)
    }

    async fn analyze_data(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are a data analyst for OverLLM.
Analyze the provided telemetry, training data, or system metrics.
Provide actionable insights and recommendations."#;

        let user_prompt = format!(
            "Data analysis request: {}\n\nContext: {}",
            task.description, task.context
        );

        let response = self.chat_completion(system_prompt, &user_prompt).await?;
        Ok(response)
    }

    async fn improve_training(&self, task: &MetaLLMTask) -> Result<String, String> {
        let system_prompt = r#"You are an ML training specialist for OverLLM.
Analyze the training pipeline and suggest improvements for:
- Data quality and diversity
- Training hyperparameters
- Loss functions and objectives
- Evaluation metrics
Provide concrete implementation suggestions."#;

        let user_prompt = format!(
            "Training improvement request: {}\n\nContext: {}\n\nCurrent training config:\n{}",
            task.description,
            task.context,
            self.get_training_config().await
        );

        let response = self.chat_completion(system_prompt, &user_prompt).await?;
        Ok(response)
    }

    async fn chat_completion(&self, system: &str, user: &str) -> Result<String, String> {
        let request = CreateChatCompletionRequestArgs::default()
            .model(&self.model)
            .messages([
                ChatCompletionRequestSystemMessageArgs::default()
                    .content(system)
                    .build()
                    .map_err(|e| format!("Failed to build system message: {}", e))?
                    .into(),
                ChatCompletionRequestUserMessageArgs::default()
                    .content(user)
                    .build()
                    .map_err(|e| format!("Failed to build user message: {}", e))?
                    .into(),
            ])
            .build()
            .map_err(|e| format!("Failed to build request: {}", e))?;

        let response = self
            .client
            .chat()
            .create(request)
            .await
            .map_err(|e| format!("Chat completion failed: {}", e))?;

        Ok(response
            .choices
            .first()
            .and_then(|c| c.message.content.as_ref())
            .cloned()
            .unwrap_or_default())
    }

    async fn record_code_suggestion(&self, task: &MetaLLMTask, result: &str) {
        let suggestion = CodeSuggestion {
            file_path: task.id.clone(),
            old_code: task.context.clone(),
            new_code: result.to_string(),
            explanation: format!("Generated for task: {}", task.description),
            confidence: 0.8,
        };

        let mut history = self.code_history.write().await;
        history.push(suggestion);
    }

    async fn get_model_state(&self) -> String {
        let state = self.overllm_state.read().await;
        serde_json::to_string_pretty(&*state).unwrap_or_else(|_| "{}".to_string())
    }

    async fn get_architecture_overview(&self) -> String {
        r#"
OverLLM Architecture:
- C++: Inference engine (transformer, attention, tensor ops)
- Go: Agent/Orchestrator (Ollama client, DPO loop, HTTP API)
- Rust: Telemetry daemon (system monitoring, vector search, DAG memory)
- Python: Training bridge (data generation, DPO trainer)
        "#.to_string()
    }

    async fn get_relevant_code(&self, context: &str) -> String {
        // In production, search codebase for relevant snippets
        format!("Context: {}", context)
    }

    async fn get_training_config(&self) -> String {
        r#"
Training Configuration:
- Method: DPO (Direct Preference Optimization)
- Beta: 0.1
- Batch size: 4
- Learning rate: 1e-3
- Epochs: 10
- Vocab size: 43 (v1)
- Model: d_model=64, n_heads=2, n_layers=2
        "#.to_string()
    }

    pub async fn update_state(&self, key: String, value: String) {
        let mut state = self.overllm_state.write().await;
        state.insert(key, value);
    }

    pub async fn get_code_history(&self) -> Vec<CodeSuggestion> {
        let history = self.code_history.read().await;
        history.clone()
    }

    pub async fn auto_improve_loop(&self, interval_secs: u64) {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(interval_secs));
        
        loop {
            interval.tick().await;
            
            // Analyze current performance
            let task = MetaLLMTask {
                id: format!("auto_{}", chrono::Utc::now().timestamp()),
                task_type: TaskType::ImproveTraining,
                description: "Auto-generate training improvements based on recent performance".to_string(),
                context: self.get_model_state().await,
                status: TaskStatus::Pending,
                result: None,
                timestamp: chrono::Utc::now().timestamp(),
            };
            
            self.add_task(task).await;
            
            // Process tasks
            if let Err(e) = self.process_tasks().await {
                eprintln!("Auto-improve failed: {}", e);
            }
        }
    }
}
