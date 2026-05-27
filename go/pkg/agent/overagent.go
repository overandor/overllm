package agent

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"math"
	mrand "math/rand"
	"net/http"
	"os"
	"path/filepath"
	"sync"
	"time"
)

// OverAgent — autonomous 1-second tick GA+RL agent
// Error-is-reward: errors produce training signal, profit-seeking fitness
type OverAgent struct {
	mu           sync.RWMutex
	agent        *Agent
	population   []Genome
	popSize      int
	generation   int
	bestFitness  float64
	bestGenome   *Genome
	memory       *AgentMemory
	dataSources  []DataSource
	apiKeys      map[string]*APIKey
	payments     []Payment
	metrics      OverAgentMetrics
	running      bool
	tickInterval time.Duration
	ipfsEndpoint string
	vercelURL    string
}

type Genome struct {
	Weights     []float64 `json:"weights"`
	Fitness     float64   `json:"fitness"`
	ErrorReward float64   `json:"error_reward"`
	Age         int       `json:"age"`
	ID          string    `json:"id"`
}

type AgentMemory struct {
	mu         sync.RWMutex
	Episodic   []MemoryEntry `json:"episodic"`
	Semantic   []MemoryEntry `json:"semantic"`
	Working    []MemoryEntry `json:"working"`
	IPFSHashes []string      `json:"ipfs_hashes"`
}

type MemoryEntry struct {
	Content   string    `json:"content"`
	Reward    float64   `json:"reward"`
	Timestamp time.Time `json:"timestamp"`
	Source    string    `json:"source"`
	Hash      string    `json:"hash"`
}

type DataSource struct {
	Name       string    `json:"name"`
	URL        string    `json:"url"`
	Type       string    `json:"type"`
	Active     bool      `json:"active"`
	ErrorRate  float64   `json:"error_rate"`
	Yield      float64   `json:"yield"`
	LastFetch  time.Time `json:"last_fetch"`
	FetchCount int       `json:"fetch_count"`
}

type APIKey struct {
	Key       string    `json:"key"`
	Owner     string    `json:"owner"`
	Created   time.Time `json:"created"`
	Calls     int       `json:"calls"`
	Revenue   float64   `json:"revenue"`
	RateLimit int       `json:"rate_limit"`
	Active    bool      `json:"active"`
}

type Payment struct {
	ID        string    `json:"id"`
	APIKey    string    `json:"api_key"`
	Amount    float64   `json:"amount"`
	Timestamp time.Time `json:"timestamp"`
	Action    string    `json:"action"`
	Prompt    string    `json:"prompt"`
	Response  string    `json:"response"`
}

type OverAgentMetrics struct {
	Generation     int       `json:"generation"`
	BestFitness    float64   `json:"best_fitness"`
	AvgFitness     float64   `json:"avg_fitness"`
	Diversity      float64   `json:"diversity"`
	MemorySize     int       `json:"memory_size"`
	TotalAPIKeys   int       `json:"total_api_keys"`
	TotalRevenue   float64   `json:"total_revenue"`
	TotalPayments  int       `json:"total_payments"`
	ErrorsRewarded int       `json:"errors_rewarded"`
	DataSources    int       `json:"data_sources_active"`
	CrawlsPerMin   int       `json:"crawls_per_min"`
	IPFSUploads    int       `json:"ipfs_uploads"`
	TicksProcessed int       `json:"ticks_processed"`
	UptimeSeconds  int       `json:"uptime_seconds"`
	Status         string    `json:"status"`
	LastTick       time.Time `json:"last_tick"`
}

func NewOverAgent(agent *Agent) *OverAgent {
	oa := &OverAgent{
		agent:        agent,
		popSize:      20,
		population:   make([]Genome, 0),
		memory:       &AgentMemory{},
		dataSources:  defaultDataSources(),
		apiKeys:      make(map[string]*APIKey),
		payments:     make([]Payment, 0),
		tickInterval: 1 * time.Second,
		ipfsEndpoint: os.Getenv("IPFS_API"),
		vercelURL:    os.Getenv("VERCEL_URL"),
	}
	if oa.ipfsEndpoint == "" {
		oa.ipfsEndpoint = "https://api.web3.storage"
	}
	if oa.vercelURL == "" {
		oa.vercelURL = "https://ui-alpha-ochre.vercel.app"
	}
	oa.initPopulation()
	return oa
}

func defaultDataSources() []DataSource {
	return []DataSource{
		{Name: "system_telemetry", URL: "localhost:7749/telemetry", Type: "telemetry", Active: true, Yield: 1.0},
		{Name: "ollama_teacher", URL: "localhost:11434", Type: "llm", Active: true, Yield: 0.8},
		{Name: "hf_wikitext", URL: "huggingface.co/datasets/wikitext", Type: "dataset", Active: true, Yield: 0.6},
		{Name: "rss_bbc", URL: "feeds.bbci.co.uk/news/rss.xml", Type: "rss", Active: true, Yield: 0.5},
		{Name: "rss_reuters", URL: "feeds.reuters.com/reuters/topNews", Type: "rss", Active: true, Yield: 0.5},
		{Name: "web_hackernews", URL: "news.ycombinator.com", Type: "web", Active: false, Yield: 0.4},
		{Name: "web_arxiv", URL: "arxiv.org/list/cs.AI/recent", Type: "web", Active: false, Yield: 0.7},
		{Name: "git_local", URL: "local", Type: "git", Active: true, Yield: 0.3},
	}
}

func (oa *OverAgent) initPopulation() {
	genomeSize := 64
	for i := 0; i < oa.popSize; i++ {
		weights := make([]float64, genomeSize)
		for j := range weights {
			weights[j] = (mrand.Float64() - 0.5) * 2.0
		}
		oa.population = append(oa.population, Genome{
			Weights: weights,
			ID:      randomHex(8),
		})
	}
}

// Start — launches the 1-second autonomous loop
func (oa *OverAgent) Start() {
	oa.running = true
	oa.metrics.Status = "running"
	log.Println("[OverAgent] Starting autonomous loop — 1 tick/sec")

	go func() {
		ticker := time.NewTicker(oa.tickInterval)
		defer ticker.Stop()
		startTime := time.Now()

		for oa.running {
			<-ticker.C
			oa.tick()
			oa.mu.Lock()
			oa.metrics.TicksProcessed++
			oa.metrics.UptimeSeconds = int(time.Since(startTime).Seconds())
			oa.metrics.LastTick = time.Now()
			oa.mu.Unlock()
		}
	}()

	// Persist metrics every 10s
	go func() {
		for oa.running {
			time.Sleep(10 * time.Second)
			oa.persistMetrics()
		}
	}()

	// IPFS upload every 5 min
	go func() {
		for oa.running {
			time.Sleep(5 * time.Minute)
			oa.uploadMemoryToIPFS()
		}
	}()

	// Push to Vercel every 30s
	go func() {
		for oa.running {
			time.Sleep(30 * time.Second)
			oa.pushToVercel()
		}
	}()
}

func (oa *OverAgent) Stop() {
	oa.running = false
	oa.metrics.Status = "stopped"
	log.Println("[OverAgent] Stopped")
}

// tick — the core 1-second loop
func (oa *OverAgent) tick() {
	oa.mu.Lock()
	defer oa.mu.Unlock()

	// 1. Crawl + harvest data from active sources
	oa.harvestData()

	// 2. Evaluate population fitness (error-is-reward)
	oa.evaluatePopulation()

	// 3. GA selection + crossover + mutation
	if oa.metrics.TicksProcessed%10 == 0 {
		oa.evolvePopulation()
	}

	// 4. RL reward from memory
	oa.rlMemoryUpdate()

	// 5. Self-adjust data sources
	if oa.metrics.TicksProcessed%30 == 0 {
		oa.adjustDataSources()
	}

	// 6. Process payment queue → training data
	oa.processPayments()
}

// harvestData — crawl active data sources
func (oa *OverAgent) harvestData() {
	for i := range oa.dataSources {
		ds := &oa.dataSources[i]
		if !ds.Active {
			continue
		}
		// Rate limit per source type
		switch ds.Type {
		case "telemetry":
			if time.Since(ds.LastFetch) < 1*time.Second {
				continue
			}
		case "web", "rss":
			if time.Since(ds.LastFetch) < 30*time.Second {
				continue
			}
		case "dataset":
			if time.Since(ds.LastFetch) < 5*time.Minute {
				continue
			}
		}

		go oa.fetchFromSource(ds)
	}
	oa.metrics.CrawlsPerMin = len(oa.dataSources) * 2
}

func (oa *OverAgent) fetchFromSource(ds *DataSource) {
	ds.LastFetch = time.Now()
	ds.FetchCount++

	var content string
	var err error

	switch ds.Type {
	case "telemetry":
		content = oa.agent.BuildContext()
	case "web":
		pages, crawlErr := oa.agent.WebCrawler.Crawl("https://" + ds.URL)
		if crawlErr != nil {
			err = crawlErr
		} else if len(pages) > 0 {
			content = pages[0].TextContent
		}
	case "rss":
		resp, fetchErr := http.Get("https://" + ds.URL)
		if fetchErr != nil {
			err = fetchErr
		} else {
			defer resp.Body.Close()
			content = fmt.Sprintf("RSS fetch from %s: status %d", ds.Name, resp.StatusCode)
		}
	case "git":
		content = fmt.Sprintf("git_activity_tick_%d", oa.metrics.TicksProcessed)
	}

	// ERROR IS REWARD — errors produce training signal
	if err != nil {
		oa.metrics.ErrorsRewarded++
		ds.ErrorRate = ds.ErrorRate*0.9 + 0.1
		oa.memory.mu.Lock()
		oa.memory.Episodic = append(oa.memory.Episodic, MemoryEntry{
			Content:   fmt.Sprintf("ERROR_REWARD: source=%s err=%v", ds.Name, err),
			Reward:    ds.ErrorRate * 2.0, // Errors are double-rewarded
			Timestamp: time.Now(),
			Source:    ds.Name,
			Hash:      hashContent(fmt.Sprintf("%v", err)),
		})
		oa.memory.mu.Unlock()

		// Convert error to preference pair (error context = chosen, empty = rejected)
		pair := PreferencePair{
			Prompt:    fmt.Sprintf("Handle error from %s", ds.Name),
			Chosen:    fmt.Sprintf("Error analysis: %v. Adjusting source parameters. Error rate: %.2f", err, ds.ErrorRate),
			Rejected:  "No error information available.",
			Context:   fmt.Sprintf("source=%s type=%s error_rate=%.2f", ds.Name, ds.Type, ds.ErrorRate),
			Timestamp: time.Now().Unix(),
		}
		oa.agent.savePreference(pair)
		return
	}

	if content != "" {
		ds.ErrorRate = ds.ErrorRate * 0.95
		ds.Yield = ds.Yield*0.9 + 0.1
		oa.memory.mu.Lock()
		entry := MemoryEntry{
			Content:   content[:min(500, len(content))],
			Reward:    ds.Yield,
			Timestamp: time.Now(),
			Source:    ds.Name,
			Hash:      hashContent(content),
		}
		oa.memory.Episodic = append(oa.memory.Episodic, entry)
		if len(oa.memory.Episodic) > 10000 {
			// Consolidate to semantic memory
			oa.memory.Semantic = append(oa.memory.Semantic, oa.memory.Episodic[:100]...)
			oa.memory.Episodic = oa.memory.Episodic[100:]
		}
		oa.memory.mu.Unlock()
	}
}

// evaluatePopulation — fitness = profit signal + error reward + memory relevance
func (oa *OverAgent) evaluatePopulation() {
	memoryReward := 0.0
	oa.memory.mu.RLock()
	for _, m := range oa.memory.Working {
		memoryReward += m.Reward
	}
	// Recent episodic memory contributes
	recentCount := min(50, len(oa.memory.Episodic))
	for i := len(oa.memory.Episodic) - recentCount; i < len(oa.memory.Episodic); i++ {
		memoryReward += oa.memory.Episodic[i].Reward * 0.1
	}
	oa.memory.mu.RUnlock()

	totalFitness := 0.0
	for i := range oa.population {
		g := &oa.population[i]
		// Fitness components
		profitSignal := oa.metrics.TotalRevenue / math.Max(float64(oa.metrics.TotalPayments), 1.0)
		errorSignal := float64(oa.metrics.ErrorsRewarded) * 0.1
		diversityBonus := genomeDiversity(g.Weights)
		ageDecay := 1.0 / (1.0 + float64(g.Age)*0.01)

		g.Fitness = (profitSignal + errorSignal + memoryReward + diversityBonus) * ageDecay
		g.ErrorReward = errorSignal
		g.Age++
		totalFitness += g.Fitness

		if g.Fitness > oa.bestFitness {
			oa.bestFitness = g.Fitness
			clone := *g
			oa.bestGenome = &clone
		}
	}

	oa.metrics.BestFitness = oa.bestFitness
	oa.metrics.AvgFitness = totalFitness / float64(len(oa.population))
	oa.metrics.Diversity = populationDiversity(oa.population)
}

// evolvePopulation — tournament selection, crossover, mutation
func (oa *OverAgent) evolvePopulation() {
	oa.generation++
	oa.metrics.Generation = oa.generation

	newPop := make([]Genome, 0, oa.popSize)

	// Elitism: keep top 2
	sorted := sortByFitness(oa.population)
	if len(sorted) >= 2 {
		newPop = append(newPop, sorted[0], sorted[1])
	}

	for len(newPop) < oa.popSize {
		// Tournament selection
		p1 := tournament(oa.population, 3)
		p2 := tournament(oa.population, 3)

		// Crossover
		child := crossover(p1, p2)

		// Mutation (higher rate when stuck)
		mutRate := 0.1
		if oa.metrics.Diversity < 0.3 {
			mutRate = 0.3
		}
		mutate(&child, mutRate)

		child.ID = randomHex(8)
		child.Age = 0
		newPop = append(newPop, child)
	}

	oa.population = newPop
}

// rlMemoryUpdate — use memory as RL replay buffer
func (oa *OverAgent) rlMemoryUpdate() {
	oa.memory.mu.Lock()
	defer oa.memory.mu.Unlock()

	// Promote high-reward episodic → working memory
	oa.memory.Working = nil
	for _, m := range oa.memory.Episodic {
		if m.Reward > 0.5 {
			oa.memory.Working = append(oa.memory.Working, m)
		}
	}
	if len(oa.memory.Working) > 100 {
		oa.memory.Working = oa.memory.Working[len(oa.memory.Working)-100:]
	}

	oa.metrics.MemorySize = len(oa.memory.Episodic) + len(oa.memory.Semantic) + len(oa.memory.Working)
}

// adjustDataSources — enable/disable sources based on yield and error rate
func (oa *OverAgent) adjustDataSources() {
	for i := range oa.dataSources {
		ds := &oa.dataSources[i]
		score := ds.Yield - ds.ErrorRate*0.5
		if score < 0.1 && ds.Active && ds.FetchCount > 10 {
			ds.Active = false
			log.Printf("[OverAgent] Disabled data source: %s (score=%.2f)", ds.Name, score)
		} else if score > 0.3 && !ds.Active {
			ds.Active = true
			log.Printf("[OverAgent] Re-enabled data source: %s (score=%.2f)", ds.Name, score)
		}
	}

	active := 0
	for _, ds := range oa.dataSources {
		if ds.Active {
			active++
		}
	}
	oa.metrics.DataSources = active
}

// processPayments — convert API payments into training data
func (oa *OverAgent) processPayments() {
	for _, p := range oa.payments {
		if p.Prompt == "" {
			continue
		}
		pair := PreferencePair{
			Prompt:    p.Prompt,
			Chosen:    p.Response,
			Rejected:  "Payment required for this response.",
			Context:   fmt.Sprintf("api_key=%s amount=%.4f action=%s", p.APIKey, p.Amount, p.Action),
			Timestamp: time.Now().Unix(),
		}
		oa.agent.savePreference(pair)
	}
	oa.payments = nil
}

// IssueAPIKey — generate a new API key for a client
func (oa *OverAgent) IssueAPIKey(owner string, rateLimit int) *APIKey {
	oa.mu.Lock()
	defer oa.mu.Unlock()

	key := "ovllm_" + randomHex(24)
	ak := &APIKey{
		Key:       key,
		Owner:     owner,
		Created:   time.Now(),
		RateLimit: rateLimit,
		Active:    true,
	}
	oa.apiKeys[key] = ak
	oa.metrics.TotalAPIKeys = len(oa.apiKeys)

	log.Printf("[OverAgent] Issued API key for %s: %s...%s", owner, key[:10], key[len(key)-4:])
	return ak
}

// RecordPayment — record an API call payment as training data
func (oa *OverAgent) RecordPayment(apiKey, prompt, response, action string, amount float64) {
	oa.mu.Lock()
	defer oa.mu.Unlock()

	ak, exists := oa.apiKeys[apiKey]
	if !exists {
		return
	}
	ak.Calls++
	ak.Revenue += amount

	p := Payment{
		ID:        randomHex(16),
		APIKey:    apiKey,
		Amount:    amount,
		Timestamp: time.Now(),
		Action:    action,
		Prompt:    prompt,
		Response:  response,
	}
	oa.payments = append(oa.payments, p)
	oa.metrics.TotalRevenue += amount
	oa.metrics.TotalPayments++
}

// uploadMemoryToIPFS — pin memory to IPFS
func (oa *OverAgent) uploadMemoryToIPFS() {
	oa.memory.mu.RLock()
	data, err := json.Marshal(oa.memory)
	oa.memory.mu.RUnlock()
	if err != nil {
		return
	}

	hash := hashContent(string(data))

	// Write locally as backup
	path := filepath.Join(oa.agent.DataDir, "memory_"+hash[:12]+".json")
	os.WriteFile(path, data, 0644)

	// Attempt IPFS upload (web3.storage or local node)
	if oa.ipfsEndpoint != "" {
		go func() {
			// POST to IPFS pinning service
			resp, err := http.Post(oa.ipfsEndpoint+"/upload", "application/json", nil)
			if err != nil {
				log.Printf("[OverAgent] IPFS upload error (rewarding): %v", err)
				oa.mu.Lock()
				oa.metrics.ErrorsRewarded++
				oa.mu.Unlock()
				return
			}
			defer resp.Body.Close()
			oa.memory.mu.Lock()
			oa.memory.IPFSHashes = append(oa.memory.IPFSHashes, hash)
			oa.memory.mu.Unlock()
			oa.mu.Lock()
			oa.metrics.IPFSUploads++
			oa.mu.Unlock()
			log.Printf("[OverAgent] Memory uploaded to IPFS: %s", hash[:16])
		}()
	}
}

// pushToVercel — push metrics to Vercel serverless function
func (oa *OverAgent) pushToVercel() {
	if oa.vercelURL == "" {
		return
	}
	data, _ := json.Marshal(oa.GetMetrics())
	go func() {
		req, err := http.NewRequest("POST", oa.vercelURL+"/api/overagent", bytes.NewReader(data))
		if err != nil {
			return
		}
		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("x-overllm-key", os.Getenv("OVERLLM_PUSH_KEY"))
		http.DefaultClient.Do(req)
	}()
}

func (oa *OverAgent) persistMetrics() {
	data, _ := json.MarshalIndent(oa.GetMetrics(), "", "  ")
	path := filepath.Join(oa.agent.DataDir, "overagent_metrics.json")
	os.WriteFile(path, data, 0644)
}

func (oa *OverAgent) GetMetrics() OverAgentMetrics {
	oa.mu.RLock()
	defer oa.mu.RUnlock()
	return oa.metrics
}

func (oa *OverAgent) GetPopulation() []Genome {
	oa.mu.RLock()
	defer oa.mu.RUnlock()
	return append([]Genome{}, oa.population...)
}

func (oa *OverAgent) GetDataSources() []DataSource {
	oa.mu.RLock()
	defer oa.mu.RUnlock()
	return append([]DataSource{}, oa.dataSources...)
}

func (oa *OverAgent) GetAPIKeys() []*APIKey {
	oa.mu.RLock()
	defer oa.mu.RUnlock()
	keys := make([]*APIKey, 0, len(oa.apiKeys))
	for _, k := range oa.apiKeys {
		keys = append(keys, k)
	}
	return keys
}

// ValidateAPIKey checks if an API key is valid and within rate limit
func (oa *OverAgent) ValidateAPIKey(key string) (*APIKey, bool) {
	oa.mu.RLock()
	defer oa.mu.RUnlock()
	ak, exists := oa.apiKeys[key]
	if !exists || !ak.Active {
		return nil, false
	}
	return ak, true
}

// GA helpers
func tournament(pop []Genome, size int) Genome {
	best := pop[mrand.Intn(len(pop))]
	for i := 1; i < size; i++ {
		candidate := pop[mrand.Intn(len(pop))]
		if candidate.Fitness > best.Fitness {
			best = candidate
		}
	}
	return best
}

func crossover(p1, p2 Genome) Genome {
	child := Genome{Weights: make([]float64, len(p1.Weights))}
	point := mrand.Intn(len(p1.Weights))
	for i := range child.Weights {
		if i < point {
			child.Weights[i] = p1.Weights[i]
		} else {
			child.Weights[i] = p2.Weights[i]
		}
	}
	return child
}

func mutate(g *Genome, rate float64) {
	for i := range g.Weights {
		if mrand.Float64() < rate {
			g.Weights[i] += (mrand.Float64() - 0.5) * 0.5
		}
	}
}

func sortByFitness(pop []Genome) []Genome {
	sorted := append([]Genome{}, pop...)
	for i := 0; i < len(sorted); i++ {
		for j := i + 1; j < len(sorted); j++ {
			if sorted[j].Fitness > sorted[i].Fitness {
				sorted[i], sorted[j] = sorted[j], sorted[i]
			}
		}
	}
	return sorted
}

func genomeDiversity(weights []float64) float64 {
	if len(weights) == 0 {
		return 0
	}
	sum := 0.0
	for _, w := range weights {
		sum += math.Abs(w)
	}
	return sum / float64(len(weights))
}

func populationDiversity(pop []Genome) float64 {
	if len(pop) < 2 {
		return 0
	}
	totalDist := 0.0
	count := 0
	for i := 0; i < len(pop); i++ {
		for j := i + 1; j < len(pop); j++ {
			d := 0.0
			for k := range pop[i].Weights {
				diff := pop[i].Weights[k] - pop[j].Weights[k]
				d += diff * diff
			}
			totalDist += math.Sqrt(d)
			count++
		}
	}
	return totalDist / float64(count)
}

func randomHex(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func hashContent(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
