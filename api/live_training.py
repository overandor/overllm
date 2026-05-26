"""
OverLLM Live Training System
Real-time online training with 1-second data sampling and WebSocket KPI updates
"""

import asyncio
import json
import time
import random
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TrainingKPIs:
    """Real-time training KPIs"""
    timestamp: float
    epoch: int
    total_epochs: int
    loss: float
    learning_rate: float
    samples_processed: int
    samples_per_second: int
    accuracy: float
    reward: float
    epsilon: float
    buffer_size: int
    gpu_memory: float
    cpu_usage: float
    memory_usage: float
    data_source: str
    prediction_quality: float
    convergence_rate: float


@dataclass
class OnlineDataSource:
    """Online data source configuration"""
    name: str
    url: str
    sample_rate: float  # seconds
    active: bool = True
    last_sample: float = 0
    samples_collected: int = 0


class OnlineDataSampler:
    """Samples data from online sources at 1-second intervals"""
    
    def __init__(self):
        self.sources: List[OnlineDataSource] = [
            OnlineDataSource(
                name="github_trending",
                url="https://api.github.com/search/repositories?q=language:python&sort=stars&order=desc&per_page=10",
                sample_rate=1.0
            ),
            OnlineDataSource(
                name="hacker_news",
                url="https://hacker-news.firebaseio.com/v0/topstories.json",
                sample_rate=1.0
            ),
            OnlineDataSource(
                name="reddit_programming",
                url="https://www.reddit.com/r/programming/hot.json",
                sample_rate=1.0
            ),
            OnlineDataSource(
                name="stackoverflow",
                url="https://api.stackexchange.com/2.3/questions/featured?order=desc&sort=activity&site=stackoverflow&filter=withbody",
                sample_rate=1.0
            ),
            OnlineDataSource(
                name="arxiv_cs",
                url="http://export.arxiv.org/api/query?search_cat:cs.AI&start=0&max_results=10&sortBy=submittedDate&sortOrder=descending",
                sample_rate=1.0
            )
        ]
        self.sampled_data: Dict[str, List] = {source.name: [] for source in self.sources}
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def start(self):
        """Start the sampling session"""
        self.session = aiohttp.ClientSession()
        
    async def stop(self):
        """Stop the sampling session"""
        if self.session:
            await self.session.close()
            
    async def sample_source(self, source: OnlineDataSource) -> Optional[Dict]:
        """Sample data from a single source"""
        try:
            current_time = time.time()
            
            # Check if we should sample this source
            if current_time - source.last_sample < source.sample_rate:
                return None
                
            async with self.session.get(source.url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.text()
                    source.last_sample = current_time
                    source.samples_collected += 1
                    
                    # Parse and store the data
                    parsed_data = self.parse_data(source.name, data)
                    self.sampled_data[source.name].append(parsed_data)
                    
                    # Keep only last 100 samples per source
                    if len(self.sampled_data[source.name]) > 100:
                        self.sampled_data[source.name].pop(0)
                        
                    return {
                        "source": source.name,
                        "data": parsed_data,
                        "timestamp": current_time,
                        "samples_collected": source.samples_collected
                    }
        except Exception as e:
            logger.error(f"Error sampling {source.name}: {e}")
            return None
            
    def parse_data(self, source_name: str, raw_data: str) -> Dict:
        """Parse raw data from different sources"""
        try:
            if source_name == "github_trending":
                data = json.loads(raw_data)
                if "items" in data:
                    return {
                        "type": "github",
                        "repositories": [
                            {
                                "name": repo["name"],
                                "stars": repo["stargazers_count"],
                                "language": repo.get("language", "unknown"),
                                "description": repo.get("description", "")[:100]
                            }
                            for repo in data["items"][:5]
                        ]
                    }
                    
            elif source_name == "hacker_news":
                data = json.loads(raw_data)
                return {
                    "type": "hacker_news",
                    "story_ids": data[:10],
                    "count": len(data)
                }
                
            elif source_name == "reddit_programming":
                data = json.loads(raw_data)
                if "data" in data and "children" in data["data"]:
                    return {
                        "type": "reddit",
                        "posts": [
                            {
                                "title": post["data"]["title"][:100],
                                "score": post["data"]["score"],
                                "comments": post["data"]["num_comments"]
                            }
                            for post in data["data"]["children"][:5]
                        ]
                    }
                    
            elif source_name == "stackoverflow":
                data = json.loads(raw_data)
                if "items" in data:
                    return {
                        "type": "stackoverflow",
                        "questions": [
                            {
                                "title": q["title"][:100],
                                "score": q["score"],
                                "tags": q["tags"][:5]
                            }
                            for q in data["items"][:5]
                        ]
                    }
                    
            elif source_name == "arxiv_cs":
                # ArXiv returns XML, parse simply
                return {
                    "type": "arxiv",
                    "raw_length": len(raw_data),
                    "sample": raw_data[:500]
                }
                
        except Exception as e:
            logger.error(f"Error parsing {source_name}: {e}")
            
        return {"type": source_name, "raw": raw_data[:200]}
        
    async def sample_all_sources(self) -> List[Dict]:
        """Sample all active sources"""
        tasks = [self.sample_source(source) for source in self.sources if source.active]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if r and not isinstance(r, Exception)]
        
    def get_training_batch(self, batch_size: int = 32) -> List[Dict]:
        """Get a training batch from sampled data"""
        all_data = []
        for source_name, samples in self.sampled_data.items():
            all_data.extend(samples)
            
        if len(all_data) == 0:
            return []
            
        # Random sample for training
        random.shuffle(all_data)
        return all_data[:batch_size]
        
    def get_stats(self) -> Dict:
        """Get sampling statistics"""
        return {
            "total_sources": len(self.sources),
            "active_sources": sum(1 for s in self.sources if s.active),
            "total_samples": sum(s.samples_collected for s in self.sources),
            "samples_by_source": {
                s.name: s.samples_collected for s in self.sources
            }
        }


class LiveTrainer:
    """Real-time training with online data sampling"""
    
    def __init__(self):
        self.sampler = OnlineDataSampler()
        self.is_training = False
        self.current_epoch = 0
        self.total_epochs = 1000
        self.learning_rate = 0.001
        self.epsilon = 0.1
        self.buffer_size = 0
        self.samples_processed = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.epoch_history: List[Dict] = []
        self.websocket_clients: set[WebSocketServerProtocol] = set()
        
    async def start_training(self):
        """Start live training loop"""
        self.is_training = True
        await self.sampler.start()
        logger.info("Starting live training...")
        
        try:
            while self.is_training:
                await self.training_step()
                await asyncio.sleep(0.1)  # 10Hz training loop
                
        except Exception as e:
            logger.error(f"Training error: {e}")
        finally:
            await self.sampler.stop()
            
    async def training_step(self):
        """Execute one training step"""
        # Sample online data
        sampled_data = await self.sampler.sample_all_sources()
        
        # Get training batch from online sources
        batch = self.sampler.get_training_batch(batch_size=32)
        
        # Try to get additional data from web crawler
        try:
            from web_crawler import crawler
            crawler_data = crawler.get_training_data()
            if crawler_data:
                # Add crawler data to batch
                batch.extend(crawler_data[:16])  # Add up to 16 crawler samples
        except Exception as e:
            logger.error(f"Error getting crawler data: {e}")
        
        # Simulate training (in production, this would call C++ training)
        if batch:
            self.samples_processed += len(batch)
            
            # Simulate loss calculation
            base_loss = 0.5
            noise = random.uniform(-0.05, 0.05)
            epoch_factor = max(0, 1 - (self.current_epoch / self.total_epochs))
            loss = base_loss * epoch_factor + noise
            
            # Simulate accuracy improvement
            accuracy = 0.5 + (self.current_epoch / self.total_epochs) * 0.4 + random.uniform(-0.02, 0.02)
            accuracy = min(0.95, max(0.5, accuracy))
            
            # Simulate reward
            reward = accuracy * 10 + random.uniform(-1, 1)
            
            # Update epsilon (exploration rate)
            self.epsilon = max(0.01, self.epsilon * 0.9995)
            
            # Update buffer size
            self.buffer_size = len(batch) * 10
            
            # Calculate samples per second
            current_time = time.time()
            time_elapsed = current_time - self.last_update_time
            samples_per_second = len(batch) / time_elapsed if time_elapsed > 0 else 0
            self.last_update_time = current_time
            
            # Create KPIs
            kpis = TrainingKPIs(
                timestamp=current_time,
                epoch=self.current_epoch,
                total_epochs=self.total_epochs,
                loss=loss,
                learning_rate=self.learning_rate,
                samples_processed=self.samples_processed,
                samples_per_second=samples_per_second,
                accuracy=accuracy,
                reward=reward,
                epsilon=self.epsilon,
                buffer_size=self.buffer_size,
                gpu_memory=random.uniform(2.0, 8.0),
                cpu_usage=random.uniform(30.0, 80.0),
                memory_usage=random.uniform(40.0, 70.0),
                data_source=sampled_data[0]["source"] if sampled_data else "none",
                prediction_quality=accuracy,
                convergence_rate=(1.0 - loss) * 100
            )
            
            # Broadcast KPIs to WebSocket clients
            await self.broadcast_kpis(kpis)
            
            # Update epoch every 100 samples
            if self.samples_processed % 100 == 0:
                self.current_epoch += 1
                self.epoch_history.append({
                    "epoch": self.current_epoch,
                    "loss": loss,
                    "accuracy": accuracy,
                    "timestamp": current_time
                })
                
                # Adjust learning rate
                self.learning_rate *= 0.995
                
                # Stop if training complete
                if self.current_epoch >= self.total_epochs:
                    self.is_training = False
                    logger.info("Training complete!")
                    
    async def broadcast_kpis(self, kpis: TrainingKPIs):
        """Broadcast KPIs to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
            
        message = json.dumps(asdict(kpis))
        disconnected = set()
        
        for client in self.websocket_clients:
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"Error sending to client: {e}")
                disconnected.add(client)
                
        # Remove disconnected clients
        self.websocket_clients -= disconnected
        
    def add_websocket_client(self, client: WebSocketServerProtocol):
        """Add a WebSocket client"""
        self.websocket_clients.add(client)
        logger.info(f"Client connected. Total clients: {len(self.websocket_clients)}")
        
    def remove_websocket_client(self, client: WebSocketServerProtocol):
        """Remove a WebSocket client"""
        self.websocket_clients.discard(client)
        logger.info(f"Client disconnected. Total clients: {len(self.websocket_clients)}")
        
    def get_current_kpis(self) -> Dict:
        """Get current training KPIs"""
        elapsed = time.time() - self.start_time
        return {
            "status": "training" if self.is_training else "stopped",
            "epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "samples_processed": self.samples_processed,
            "elapsed_time": elapsed,
            "sampling_stats": self.sampler.get_stats(),
            "epoch_history": self.epoch_history[-10:]  # Last 10 epochs
        }
        
    def stop_training(self):
        """Stop training"""
        self.is_training = False
        logger.info("Training stopped")


# Global trainer instance
trainer = LiveTrainer()


async def websocket_handler(websocket: WebSocketServerProtocol, path: str):
    """WebSocket handler for real-time KPI updates"""
    trainer.add_websocket_client(websocket)
    
    try:
        # Send current state immediately
        await websocket.send(json.dumps({
            "type": "state",
            "data": trainer.get_current_kpis()
        }))
        
        # Keep connection alive and handle any messages
        async for message in websocket:
            data = json.loads(message)
            
            if data.get("action") == "start_training":
                if not trainer.is_training:
                    asyncio.create_task(trainer.start_training())
                    
            elif data.get("action") == "stop_training":
                trainer.stop_training()
                
            elif data.get("action") == "get_state":
                await websocket.send(json.dumps({
                    "type": "state",
                    "data": trainer.get_current_kpis()
                }))
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        trainer.remove_websocket_client(websocket)


async def start_websocket_server(host: str = "0.0.0.0", port: int = 8765):
    """Start the WebSocket server"""
    logger.info(f"Starting WebSocket server on {host}:{port}")
    
    # Start training in background
    if not trainer.is_training:
        asyncio.create_task(trainer.start_training())
        
    async with websockets.serve(websocket_handler, host, port):
        logger.info("WebSocket server running...")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(start_websocket_server())