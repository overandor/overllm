package server

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/overllm/overllm-agent/pkg/agent"
	"github.com/overllm/overllm-agent/pkg/localmodel"
	"github.com/overllm/overllm-agent/pkg/proof"
	"github.com/overllm/overllm-agent/pkg/venture"
	"github.com/overllm/overllm-agent/pkg/webcrawler"
)

type Server struct {
	Agent           *agent.Agent
	Addr            string
	ProofHandlers   *proof.Handlers
	VentureHandlers *venture.Handlers
	Model           *localmodel.Runner
}

func New(a *agent.Agent, addr string) *Server {
	// Initialize proof handlers - point to local Rust proof daemon
	proofDaemonURL := os.Getenv("PROOF_DAEMON_URL")
	if proofDaemonURL == "" {
		proofDaemonURL = "http://localhost:8080" // Default Rust proof daemon URL
	}

	model, err := localmodel.NewFromEnv()
	if err != nil {
		log.Printf("Local model unavailable: %v", err)
	}

	return &Server{
		Agent:           a,
		Addr:            addr,
		ProofHandlers:   proof.NewHandlers(proofDaemonURL),
		VentureHandlers: venture.NewHandlers(a.DataDir),
		Model:           model,
	}
}

func (s *Server) RegisterRoutes() {
	http.HandleFunc("/api/status", s.handleStatus)
	http.HandleFunc("/api/telemetry", s.handleTelemetry)
	http.HandleFunc("/api/preference_queue", s.handlePreferenceQueue)
	http.HandleFunc("/api/generate", s.handleGenerate)
	http.HandleFunc("/api/context", s.handleContext)
	http.HandleFunc("/api/metrics", s.handleMetrics)
	http.HandleFunc("/api/model", s.handleModel)
	http.HandleFunc("/api/node", s.handleNode)
	http.HandleFunc("/api/files", s.handleFiles)
	http.HandleFunc("/api/pipeline", s.handlePipeline)
	http.HandleFunc("/api/crawler/status", s.handleCrawlerStatus)
	http.HandleFunc("/api/crawler/pages", s.handleCrawlerPages)
	http.HandleFunc("/api/crawler/start", s.handleCrawlerStart)
	http.HandleFunc("/api/crawler/stop", s.handleCrawlerStop)

	// Proof of Inference endpoints
	http.HandleFunc("/api/proof/generate", s.handleGenerateProof)
	http.HandleFunc("/api/proof/verify", s.handleVerifyProof)
	http.HandleFunc("/api/proof/billing", s.handleBillingInfo)
	http.HandleFunc("/api/proof/memory", s.handleMemoryRecord)

	// Coding Receipt endpoints - use real proof handlers
	http.HandleFunc("/api/proof/receipt", s.ProofHandlers.HandleGenerateReceipt)
	http.HandleFunc("/api/proof/receipt/", s.ProofHandlers.HandleGetReceipt)
	http.HandleFunc("/api/proof/receipts", s.ProofHandlers.HandleListReceipts)
	http.HandleFunc("/api/proof/market", s.ProofHandlers.HandleMemoryMarket)
	http.HandleFunc("/api/proof/ipfs/", s.ProofHandlers.HandleUploadToIPFS)
	http.HandleFunc("/api/proof/solana/", s.ProofHandlers.HandleAnchorToSolana)

	// VentureChain deal-formation endpoints
	http.HandleFunc("/api/venture/deals", s.VentureHandlers.HandleDealsRoot)
	http.HandleFunc("/api/venture/deals/", s.VentureHandlers.HandleDealsSubtree)

	// Breakthrough Verification Engine endpoints
	http.HandleFunc("/api/venture/claims", s.VentureHandlers.HandleClaimsRoot)
	http.HandleFunc("/api/venture/claims/", s.VentureHandlers.HandleClaimsSubtree)

	// OverAgent autonomous agent endpoints
	http.HandleFunc("/api/overagent", s.handleOverAgent)
	http.HandleFunc("/api/overagent/keys", s.handleOverAgentKeys)
	http.HandleFunc("/api/overagent/population", s.handleOverAgentPopulation)
	http.HandleFunc("/api/overagent/datasources", s.handleOverAgentDataSources)
	http.HandleFunc("/api/overagent/memory", s.handleOverAgentMemory)
	http.HandleFunc("/api/overagent/generate", s.handleOverAgentGenerate)

	// Legacy endpoints for backward compatibility
	http.HandleFunc("/api/proofs", s.handleListProofs)
	http.HandleFunc("/api/proofs/", s.handleGetProof)
	http.HandleFunc("/api/memory-market", s.handleMemoryMarket)

	// Serve the built UI. The source index.html references /src/main.tsx and
	// only works under Vite, so production serving must prefer ui/dist.
	cwd, _ := os.Getwd()
	log.Printf("Current working directory: %s", cwd)

	uiPath := "ui/dist"
	if info, err := os.Stat(uiPath); err != nil {
		log.Printf("UI directory not found at %s: %v", uiPath, err)
		uiPath = "ui"
		if info, err := os.Stat(uiPath); err != nil {
			log.Printf("UI directory not found at %s: %v", uiPath, err)
		} else {
			log.Printf("UI directory found at %s (isDir: %v)", uiPath, info.IsDir())
		}
	} else {
		log.Printf("UI directory found at %s (isDir: %v)", uiPath, info.IsDir())
	}

	fs := http.FileServer(http.Dir(uiPath))
	http.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/api/") {
			http.NotFound(w, r)
			return
		}
		if r.URL.Path == "/" {
			http.ServeFile(w, r, uiPath+"/index.html")
			return
		}
		requested := strings.TrimPrefix(r.URL.Path, "/")
		if requested != "" {
			if _, err := os.Stat(uiPath + "/" + requested); os.IsNotExist(err) {
				http.ServeFile(w, r, uiPath+"/index.html")
				return
			}
		}
		fs.ServeHTTP(w, r)
	}))
	log.Printf("Serving UI from: %s/", uiPath)
}

func (s *Server) handleMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	home, _ := os.UserHomeDir()
	data, err := os.ReadFile(home + "/.overllm/data/training_metrics.json")
	if err != nil {
		json.NewEncoder(w).Encode(map[string]string{"status": "no_data"})
		return
	}
	w.Write(data)
}

func (s *Server) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	resp := map[string]interface{}{
		"status":     "running",
		"queue_size": s.Agent.GetQueueSize(),
		"telemetry":  len(s.Agent.Telemetry),
		"model":      "overllm-local",
		"ollama":     "disabled",
	}
	if s.Model != nil {
		resp["model_path"] = s.Model.ModelPath
		resp["vocab_path"] = s.Model.VocabPath
		resp["runtime"] = s.Model.BinaryPath
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (s *Server) handleModel(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	if s.Model == nil {
		w.WriteHeader(http.StatusServiceUnavailable)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "unavailable",
			"error":  "local model runner failed to initialize",
		})
		return
	}
	status := "ready"
	var errText string
	if err := s.Model.Validate(); err != nil {
		status = "unavailable"
		errText = err.Error()
		w.WriteHeader(http.StatusServiceUnavailable)
	}
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":     status,
		"runtime":    s.Model.BinaryPath,
		"model_path": s.Model.ModelPath,
		"vocab_path": s.Model.VocabPath,
		"timeout":    s.Model.Timeout.String(),
		"ollama":     "disabled",
		"error":      errText,
	})
}

func (s *Server) handleNode(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	host, _ := os.Hostname()
	cwd, _ := os.Getwd()
	idSeed := host + "|" + cwd
	sum := sha256.Sum256([]byte(idSeed))
	nodeID := "overllm-node-" + hex.EncodeToString(sum[:])[:16]
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"node_id":       nodeID,
		"host":          host,
		"os":            runtime.GOOS,
		"arch":          runtime.GOARCH,
		"cpus":          runtime.NumCPU(),
		"workspace":     cwd,
		"public_url":    os.Getenv("OVERLLM_PUBLIC_URL"),
		"role":          "local verifier / inference worker",
		"work_contract": "prompt -> local inference -> receipt -> confirmation",
		"chain":         "blockchain/overllm",
	})
}

func (s *Server) handleFiles(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	cwd, _ := os.Getwd()
	used := map[string]string{}
	if s.Model != nil {
		used[filepath.Clean(s.Model.ModelPath)] = "active local model weights"
		used[filepath.Clean(s.Model.VocabPath)] = "active tokenizer vocabulary"
		used[filepath.Clean(s.Model.BinaryPath)] = "active inference runtime"
	}
	used[filepath.Join(cwd, "ui", "dist", "index.html")] = "served dashboard entry"
	used[filepath.Join(os.Getenv("HOME"), ".overllm", "data", "training_metrics.json")] = "training metrics source"

	type fileInfo struct {
		Path     string `json:"path"`
		RelPath  string `json:"rel_path"`
		Size     int64  `json:"size"`
		Modified string `json:"modified"`
		InUse    bool   `json:"in_use"`
		Role     string `json:"role,omitempty"`
	}
	var files []fileInfo
	seen := map[string]bool{}
	for path, role := range used {
		if info, err := os.Stat(path); err == nil {
			rel, _ := filepath.Rel(cwd, path)
			files = append(files, fileInfo{
				Path:     path,
				RelPath:  rel,
				Size:     info.Size(),
				Modified: info.ModTime().Format(time.RFC3339),
				InUse:    true,
				Role:     role,
			})
			seen[path] = true
		}
	}
	filepath.WalkDir(cwd, func(path string, d os.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			if d != nil && d.IsDir() {
				name := d.Name()
				if name == "node_modules" || name == ".git" || name == "dist" {
					if path != cwd {
						return filepath.SkipDir
					}
				}
			}
			return nil
		}
		if len(files) >= 600 {
			return filepath.SkipAll
		}
		info, err := d.Info()
		if err != nil {
			return nil
		}
		clean := filepath.Clean(path)
		if seen[clean] {
			return nil
		}
		rel, _ := filepath.Rel(cwd, clean)
		role, inUse := used[clean]
		files = append(files, fileInfo{
			Path:     clean,
			RelPath:  rel,
			Size:     info.Size(),
			Modified: info.ModTime().Format(time.RFC3339),
			InUse:    inUse,
			Role:     role,
		})
		return nil
	})
	sort.Slice(files, func(i, j int) bool {
		if files[i].InUse != files[j].InUse {
			return files[i].InUse
		}
		return files[i].RelPath < files[j].RelPath
	})
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"workspace": cwd,
		"count":     len(files),
		"files":     files,
	})
}

func (s *Server) handlePipeline(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	modelReady := false
	if s.Model != nil && s.Model.Validate() == nil {
		modelReady = true
	}
	s.Agent.CrawlerMu.RLock()
	crawlerStatus := s.Agent.CrawlerStatus
	crawlerRunning := s.Agent.CrawlerRunning
	s.Agent.CrawlerMu.RUnlock()
	if crawlerStatus == "" {
		crawlerStatus = "idle"
	}
	stages := []map[string]interface{}{
		{"name": "collect", "status": crawlerStatus, "active": crawlerRunning, "detail": "Crawler discovers links and extracts page text."},
		{"name": "extract", "status": "ready", "detail": "Telemetry and crawled pages are normalized into context."},
		{"name": "train", "status": "complete", "detail": "DPO metrics are read from ~/.overllm/data/training_metrics.json."},
		{"name": "build", "status": boolStatus(modelReady), "detail": "Local C++ model runtime and dashboard bundle are loaded from disk."},
		{"name": "verify", "status": "ready", "detail": "Each prompt produces a receipt and model metadata."},
		{"name": "confirm", "status": "prototype", "detail": "Receipts are local/mock unless proof daemon and chain anchoring are enabled."},
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"chain":        "blockchain/overllm",
		"token_policy": "dynamic-origin tokens planned: prompt text + source citations + model receipt",
		"stages":       stages,
	})
}

func boolStatus(ok bool) string {
	if ok {
		return "ready"
	}
	return "blocked"
}

func (s *Server) handleCrawlerStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	s.Agent.CrawledPagesMu.RLock()
	pages := append([]webcrawler.Page(nil), s.Agent.CrawledPages...)
	s.Agent.CrawledPagesMu.RUnlock()
	s.Agent.CrawlerMu.RLock()
	running := s.Agent.CrawlerRunning
	status := s.Agent.CrawlerStatus
	started := s.Agent.CrawlerStarted
	finished := s.Agent.CrawlerFinished
	seeds := append([]string(nil), s.Agent.CrawlerSeeds...)
	s.Agent.CrawlerMu.RUnlock()
	if status == "" {
		status = "idle"
	}
	stats := crawlerStats(pages)
	stats["is_crawling"] = running
	stats["status"] = status
	stats["started_at"] = started
	stats["finished_at"] = finished
	if seeds == nil {
		seeds = []string{}
	}
	stats["seed_urls"] = seeds
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

func (s *Server) handleCrawlerPages(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	s.Agent.CrawledPagesMu.RLock()
	pages := append([]webcrawler.Page(nil), s.Agent.CrawledPages...)
	s.Agent.CrawledPagesMu.RUnlock()
	dto := make([]map[string]interface{}, 0, len(pages))
	for _, page := range pages {
		dto = append(dto, crawlerPageDTO(page))
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"pages": dto,
		"count": len(dto),
	})
}

func (s *Server) handleCrawlerStart(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	var req struct {
		SeedURLs       []string `json:"seed_urls"`
		MaxPages       int      `json:"max_pages"`
		MaxDepth       int      `json:"max_depth"`
		FollowExternal bool     `json:"follow_external"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}
	if len(req.SeedURLs) == 0 {
		http.Error(w, "seed_urls required", 400)
		return
	}
	if req.MaxPages <= 0 {
		req.MaxPages = 50
	}
	if req.MaxDepth <= 0 {
		req.MaxDepth = 2
	}
	s.Agent.CrawlerMu.Lock()
	if s.Agent.CrawlerRunning {
		s.Agent.CrawlerMu.Unlock()
		http.Error(w, "crawler already running", 409)
		return
	}
	s.Agent.CrawlerRunning = true
	s.Agent.CrawlerStatus = "crawling"
	s.Agent.CrawlerStarted = time.Now().Unix()
	s.Agent.CrawlerFinished = 0
	s.Agent.CrawlerSeeds = req.SeedURLs
	s.Agent.CrawlerMu.Unlock()

	go func() {
		var collected []webcrawler.Page
		for _, seed := range req.SeedURLs {
			domains := []string{}
			if !req.FollowExternal {
				if parsed, err := url.Parse(seed); err == nil {
					domains = []string{parsed.Hostname()}
				}
			}
			crawler := webcrawler.NewCrawler(req.MaxDepth, req.MaxPages)
			crawler.SetAllowedDomains(domains)
			pages, err := crawler.Crawl(seed)
			if err != nil {
				log.Printf("crawler seed %s failed: %v", seed, err)
				continue
			}
			collected = append(collected, pages...)
			if len(collected) >= req.MaxPages {
				collected = collected[:req.MaxPages]
				break
			}
		}
		s.Agent.CrawledPagesMu.Lock()
		s.Agent.CrawledPages = collected
		s.Agent.CrawledPagesMu.Unlock()
		s.Agent.CrawlerMu.Lock()
		s.Agent.CrawlerRunning = false
		s.Agent.CrawlerStatus = "complete"
		s.Agent.CrawlerFinished = time.Now().Unix()
		s.Agent.CrawlerMu.Unlock()
	}()

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "started",
		"seed_urls": req.SeedURLs,
		"max_pages": req.MaxPages,
		"max_depth": req.MaxDepth,
	})
}

func (s *Server) handleCrawlerStop(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	s.Agent.CrawlerMu.Lock()
	s.Agent.CrawlerRunning = false
	s.Agent.CrawlerStatus = "stopped"
	s.Agent.CrawlerFinished = time.Now().Unix()
	s.Agent.CrawlerMu.Unlock()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{"status": "stopped"})
}

func crawlerStats(pages []webcrawler.Page) map[string]interface{} {
	domains := map[string]int{}
	unique := map[string]bool{}
	var totalSize int
	for _, page := range pages {
		unique[page.URL] = true
		if parsed, err := url.Parse(page.URL); err == nil {
			domains[parsed.Hostname()]++
		}
		totalSize += len(page.Content)
	}
	avg := 0
	if len(pages) > 0 {
		avg = totalSize / len(pages)
	}
	return map[string]interface{}{
		"total_pages_crawled": len(pages),
		"unique_urls":         len(unique),
		"domains_crawled":     len(domains),
		"domain_breakdown":    domains,
		"avg_page_size":       avg,
	}
}

func crawlerPageDTO(page webcrawler.Page) map[string]interface{} {
	parsed, _ := url.Parse(page.URL)
	textLen := len(page.TextContent)
	wordCount := len(strings.Fields(page.TextContent))
	linkCount := len(page.Links)
	hash := sha256.Sum256([]byte(page.URL + page.TextContent))
	return map[string]interface{}{
		"url":          page.URL,
		"title":        page.Title,
		"domain":       parsed.Hostname(),
		"timestamp":    page.CrawledAt.Unix(),
		"content_hash": hex.EncodeToString(hash[:])[:24],
		"text_length":  textLen,
		"links":        page.Links,
		"depth":        page.Depth,
		"visual_features": map[string]interface{}{
			"layout_structure": map[string]int{
				"total_elements": linkCount + wordCount,
				"header_count":   strings.Count(strings.ToLower(page.Content), "<h1") + strings.Count(strings.ToLower(page.Content), "<h2"),
				"nav_count":      strings.Count(strings.ToLower(page.Content), "<nav"),
				"main_count":     strings.Count(strings.ToLower(page.Content), "<main"),
				"section_count":  strings.Count(strings.ToLower(page.Content), "<section"),
				"article_count":  strings.Count(strings.ToLower(page.Content), "<article"),
				"aside_count":    strings.Count(strings.ToLower(page.Content), "<aside"),
				"footer_count":   strings.Count(strings.ToLower(page.Content), "<footer"),
			},
			"content_density": map[string]interface{}{
				"text_to_html_ratio": safeRatio(textLen, len(page.Content)),
				"text_length":        textLen,
				"word_count":         wordCount,
			},
			"media_elements": map[string]int{
				"image_count": strings.Count(strings.ToLower(page.Content), "<img"),
				"video_count": strings.Count(strings.ToLower(page.Content), "<video"),
				"audio_count": strings.Count(strings.ToLower(page.Content), "<audio"),
			},
			"interactive_elements": map[string]int{
				"button_count": strings.Count(strings.ToLower(page.Content), "<button"),
				"form_count":   strings.Count(strings.ToLower(page.Content), "<form"),
				"link_count":   linkCount,
			},
		},
	}
}

func safeRatio(a, b int) float64 {
	if b == 0 {
		return 0
	}
	return float64(a) / float64(b)
}

func (s *Server) handleTelemetry(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	s.Agent.TelemetryMu.RLock()
	defer s.Agent.TelemetryMu.RUnlock()
	window := 200
	start := len(s.Agent.Telemetry) - window
	if start < 0 {
		start = 0
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.Agent.Telemetry[start:])
}

func (s *Server) handlePreferenceQueue(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	size := s.Agent.GetQueueSize()
	resp := map[string]interface{}{
		"queue_size": size,
		"batch_size": 4,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

type GenerateRequest struct {
	Prompt    string `json:"prompt"`
	MaxTokens int    `json:"max_tokens"`
}

func (s *Server) handleGenerate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	var req GenerateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}
	ctx := s.Agent.BuildContext()

	if s.Model == nil {
		http.Error(w, "local model unavailable", http.StatusServiceUnavailable)
		return
	}
	modelResult, err := s.Model.Generate(r.Context(), req.Prompt, req.MaxTokens)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	response := modelResult.Text

	// Generate real receipt using Rust proof daemon
	sessionID := "session_" + fmt.Sprintf("%x", len(req.Prompt))
	proofReq := proof.GenerateReceiptRequest{
		SessionID:    sessionID,
		ActionType:   "generation",
		Prompt:       []byte(req.Prompt),
		FilesTouched: []proof.FileAction{},
		CommandsRun:  []proof.CommandExec{},
		Stdout:       []byte(response),
		Stderr:       []byte{},
		ExitCode:     0,
		Diff:         []byte{},
		TestResult:   []byte{},
	}

	receipt, err := s.ProofHandlers.Client.GenerateReceipt(proofReq)
	if err != nil {
		// Fallback to mock receipt if proof daemon is unavailable
		log.Printf("Proof daemon unavailable, using mock receipt: %v", err)
		receiptID := fmt.Sprintf("gen_%x", len(req.Prompt)+len(response))
		resp := map[string]interface{}{
			"response":       response,
			"generated_text": response,
			"context":        ctx,
			"model":          modelResult,
			"receipt": map[string]interface{}{
				"receipt_id":            receiptID,
				"session_id":            sessionID,
				"prompt_hash":           fmt.Sprintf("%x", len(req.Prompt)),
				"model_id":              "overllm-v1",
				"worker_id":             "worker_001",
				"files_touched":         []string{},
				"commands_run":          []string{},
				"exit_code":             0,
				"memory_price_lamports": 1000,
				"created_at":            "2026-05-25T20:00:00Z",
				"proof_signature":       "mock_sig",
			},
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
		return
	}

	resp := map[string]interface{}{
		"response":       response,
		"generated_text": response,
		"context":        ctx,
		"model":          modelResult,
		"receipt":        receipt,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func (s *Server) handleContext(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	ctx := s.Agent.BuildContext()
	lines := strings.Split(ctx, "\n")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"context": ctx,
		"events":  len(lines),
		"summary": fmt.Sprintf("%d telemetry events in window", len(lines)),
	})
}

func (s *Server) handleGenerateProof(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"inference_id": "mock_inf_001",
		"proof_cid":    "QmMockProofCID",
		"memory_cid":   "QmMockMemoryCID",
		"success":      true,
		"message":      "Proof generation (requires Rust FFI integration)",
	})
}

func (s *Server) handleVerifyProof(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"valid": true, "message": "Mock verification"})
}

func (s *Server) handleBillingInfo(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"collateral_value": 1000,
		"trust_score":      0.9,
		"billable":         true,
		"currency":         "lamports",
	})
}

func (s *Server) handleMemoryRecord(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{"memory_cid": "QmMock", "retrieval_count": 0, "market_price": 1000})
}

func (s *Server) handleListProofs(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"receipts": []map[string]interface{}{
			{
				"receipt_id":            "mock_receipt_001",
				"session_id":            "session_001",
				"prompt_hash":           "abc123",
				"model_id":              "overllm-v1",
				"worker_id":             "worker_001",
				"files_touched":         []string{"main.go"},
				"commands_run":          []string{"go build"},
				"exit_code":             0,
				"memory_price_lamports": 1000,
				"created_at":            "2026-05-25T20:00:00Z",
			},
		},
		"total": 1,
	})
}

func (s *Server) handleGetProof(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}

	// Extract receipt_id from path
	receiptID := strings.TrimPrefix(r.URL.Path, "/api/proofs/")
	if receiptID == "" {
		http.Error(w, "Receipt ID required", 400)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"receipt_id":  receiptID,
		"session_id":  "session_001",
		"prompt_hash": "abc123",
		"model_id":    "overllm-v1",
		"worker_id":   "worker_001",
		"files_touched": []map[string]interface{}{
			{"path": "main.go", "action": "edit", "before_hash": "hash1", "after_hash": "hash2"},
		},
		"commands_run": []map[string]interface{}{
			{"command": "go build", "exit_code": 0, "stdout_hash": "hash3", "stderr_hash": "hash4", "duration_ms": 100},
		},
		"stdout_hash":           "hash3",
		"stderr_hash":           "hash4",
		"exit_code":             0,
		"diff_hash":             "hash5",
		"test_result_hash":      "hash6",
		"proof_signature":       "sig123",
		"memory_price_lamports": 1000,
		"created_at":            "2026-05-25T20:00:00Z",
		"solana_tx_signature":   nil,
	})
}

func (s *Server) handleMemoryMarket(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"total_liquidity": 10000,
		"top_memories": []map[string]interface{}{
			{"memory_cid": "QmMem1", "reuse_score": 0.95, "market_price": 9500, "retrieval_count": 100},
			{"memory_cid": "QmMem2", "reuse_score": 0.85, "market_price": 8500, "retrieval_count": 80},
		},
		"base_price":      1000,
		"pricing_formula": "base * (1 + score * 9.0)",
	})
}

// OverAgent handlers

func (s *Server) handleOverAgent(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if s.Agent.OverAgent == nil {
		json.NewEncoder(w).Encode(map[string]string{"status": "not_initialized"})
		return
	}
	json.NewEncoder(w).Encode(s.Agent.OverAgent.GetMetrics())
}

func (s *Server) handleOverAgentKeys(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if s.Agent.OverAgent == nil {
		http.Error(w, "overagent not initialized", 503)
		return
	}

	switch r.Method {
	case http.MethodGet:
		json.NewEncoder(w).Encode(map[string]interface{}{
			"keys": s.Agent.OverAgent.GetAPIKeys(),
		})
	case http.MethodPost:
		var req struct {
			Owner     string `json:"owner"`
			RateLimit int    `json:"rate_limit"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		if req.RateLimit == 0 {
			req.RateLimit = 100
		}
		key := s.Agent.OverAgent.IssueAPIKey(req.Owner, req.RateLimit)
		json.NewEncoder(w).Encode(key)
	default:
		http.Error(w, "GET or POST", 405)
	}
}

func (s *Server) handleOverAgentPopulation(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if s.Agent.OverAgent == nil {
		http.Error(w, "overagent not initialized", 503)
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{
		"population": s.Agent.OverAgent.GetPopulation(),
		"generation": s.Agent.OverAgent.GetMetrics().Generation,
	})
}

func (s *Server) handleOverAgentDataSources(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if s.Agent.OverAgent == nil {
		http.Error(w, "overagent not initialized", 503)
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{
		"sources": s.Agent.OverAgent.GetDataSources(),
	})
}

func (s *Server) handleOverAgentMemory(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if s.Agent.OverAgent == nil {
		http.Error(w, "overagent not initialized", 503)
		return
	}
	m := s.Agent.OverAgent.GetMetrics()
	json.NewEncoder(w).Encode(map[string]interface{}{
		"memory_size":  m.MemorySize,
		"ipfs_uploads": m.IPFSUploads,
	})
}

func (s *Server) handleOverAgentGenerate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Content-Type", "application/json")
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	if s.Agent.OverAgent == nil {
		http.Error(w, "overagent not initialized", 503)
		return
	}

	apiKey := r.Header.Get("x-api-key")
	ak, valid := s.Agent.OverAgent.ValidateAPIKey(apiKey)
	if !valid {
		http.Error(w, "invalid or missing API key", 401)
		return
	}

	var req struct {
		Prompt string `json:"prompt"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), 400)
		return
	}

	ctx := s.Agent.BuildContext()
	response := fmt.Sprintf("[OverAgent gen=%d] %s (context=%d)", s.Agent.OverAgent.GetMetrics().Generation, req.Prompt, len(ctx))

	s.Agent.OverAgent.RecordPayment(apiKey, req.Prompt, response, "generate", 0.001)

	json.NewEncoder(w).Encode(map[string]interface{}{
		"response":   response,
		"api_key":    ak.Key[:10] + "...",
		"calls":      ak.Calls,
		"generation": s.Agent.OverAgent.GetMetrics().Generation,
	})
}

func (s *Server) Run() error {
	s.RegisterRoutes()
	fmt.Printf("[Server] Listening on %s\n", s.Addr)
	return http.ListenAndServe(s.Addr, nil)
}
