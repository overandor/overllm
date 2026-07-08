package agent

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/overllm/overllm-agent/pkg/webcrawler"
)

type TelemetryEvent struct {
	Timestamp int64  `json:"timestamp"`
	Type      string `json:"type,omitempty"`
	EventType string `json:"event_type,omitempty"`
	Data      string `json:"data"`
}

// Normalize accepts both the original Go field name (`type`) and the Rust
// daemon field name (`event_type`). Without this bridge, telemetry can be
// accepted by the server but silently ignored by BuildContext.
func (ev *TelemetryEvent) Normalize() {
	if ev.Type == "" {
		ev.Type = ev.EventType
	}
	if ev.EventType == "" {
		ev.EventType = ev.Type
	}
}

func (ev TelemetryEvent) Kind() string {
	if ev.Type != "" {
		return ev.Type
	}
	return ev.EventType
}

type PreferencePair struct {
	Prompt    string `json:"prompt"`
	Chosen    string `json:"chosen"`
	Rejected  string `json:"rejected"`
	Context   string `json:"context"`
	Timestamp int64  `json:"timestamp"`
}

type Agent struct {
	Telemetry       []TelemetryEvent
	TelemetryMu     sync.RWMutex
	PreferenceQueue []PreferencePair
	QueueMu         sync.Mutex
	DataDir         string
	Prompts         []string
	Running         bool
	WebCrawler      *webcrawler.Crawler
	CrawledPages    []webcrawler.Page
	CrawledPagesMu  sync.RWMutex
	CrawlerRunning  bool
	CrawlerStatus   string
	CrawlerStarted  int64
	CrawlerFinished int64
	CrawlerSeeds    []string
	CrawlerMu       sync.RWMutex
	OverAgent       *OverAgent
}

func NewAgent() *Agent {
	dir := filepath.Join(os.Getenv("HOME"), ".overllm", "data")
	os.MkdirAll(dir, 0755)
	a := &Agent{
		DataDir:    dir,
		WebCrawler: webcrawler.NewCrawler(3, 50), // max depth 3, max 50 pages
		Prompts: []string{
			"What should I work on next?",
			"Summarize my recent activity.",
			"What files have I been editing?",
			"How is my system performing?",
			"What apps are consuming resources?",
			"Generate a task list based on my context.",
		},
	}
	a.OverAgent = NewOverAgent(a)
	return a
}

func (a *Agent) StartCollector() {
	a.Running = true
	http.HandleFunc("/telemetry", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", 405)
			return
		}
		body, _ := io.ReadAll(r.Body)
		var ev TelemetryEvent
		if err := json.Unmarshal(body, &ev); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		ev.Normalize()
		if ev.Kind() == "" {
			http.Error(w, "telemetry event type is required", 400)
			return
		}
		a.TelemetryMu.Lock()
		a.Telemetry = append(a.Telemetry, ev)
		if len(a.Telemetry) > 10000 {
			a.Telemetry = a.Telemetry[len(a.Telemetry)-5000:]
		}
		a.TelemetryMu.Unlock()
		w.WriteHeader(200)
	})

	// Web crawling endpoint
	http.HandleFunc("/api/crawl", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", 405)
			return
		}

		var req struct {
			StartURL       string   `json:"start_url"`
			AllowedDomains []string `json:"allowed_domains"`
		}

		body, _ := io.ReadAll(r.Body)
		if err := json.Unmarshal(body, &req); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}

		err := a.CrawlWebsite(req.StartURL, req.AllowedDomains)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"status": "crawled",
			"pages":  len(a.CrawledPages),
		})
	})

	// Web search endpoint
	http.HandleFunc("/api/search", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", 405)
			return
		}

		var req struct {
			Query string `json:"query"`
		}

		body, _ := io.ReadAll(r.Body)
		if err := json.Unmarshal(body, &req); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}

		results := a.SearchWeb(req.Query)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"query":   req.Query,
			"results": results,
		})
	})

	// Generation with web context
	http.HandleFunc("/api/generate_with_web", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "POST only", 405)
			return
		}

		var req struct {
			Prompt string `json:"prompt"`
		}

		body, _ := io.ReadAll(r.Body)
		if err := json.Unmarshal(body, &req); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}

		response, err := a.GenerateWithWebContext(req.Prompt)
		if err != nil {
			http.Error(w, err.Error(), 500)
			return
		}

		json.NewEncoder(w).Encode(map[string]interface{}{
			"response": response,
		})
	})

	go a.generationLoop()
}

func (a *Agent) BuildContext() string {
	a.TelemetryMu.RLock()
	defer a.TelemetryMu.RUnlock()
	if len(a.Telemetry) == 0 {
		return ""
	}
	var parts []string
	window := 100
	start := len(a.Telemetry) - window
	if start < 0 {
		start = 0
	}
	for _, ev := range a.Telemetry[start:] {
		switch ev.Kind() {
		case "active_app":
			parts = append(parts, fmt.Sprintf("Active app: %s", ev.Data))
		case "file_access":
			parts = append(parts, fmt.Sprintf("File: %s", ev.Data))
		case "process":
			parts = append(parts, fmt.Sprintf("Process: %s", ev.Data))
		case "network":
			parts = append(parts, fmt.Sprintf("Network: %s", ev.Data))
		case "cpu_ram":
			parts = append(parts, fmt.Sprintf("System: %s", ev.Data))
		case "click":
			parts = append(parts, fmt.Sprintf("Click: %s", ev.Data))
		}
	}
	return strings.Join(parts, "\n")
}

func (a *Agent) generationLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	for a.Running {
		<-ticker.C
		ctx := a.BuildContext()
		for _, prompt := range a.Prompts {
			// Placeholder for generation without Ollama dependency.
			// This is intentionally only logged; production generation is served
			// through the configured localmodel runner in the HTTP layer.
			log.Printf("Processing prompt: %s with context length: %d", prompt, len(ctx))
		}
	}
}

func (a *Agent) savePreference(pair PreferencePair) {
	path := filepath.Join(a.DataDir, "preferences.jsonl")
	f, err := os.OpenFile(path, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if err != nil {
		return
	}
	defer f.Close()
	b, _ := json.Marshal(pair)
	f.Write(b)
	f.Write([]byte("\n"))
}

func (a *Agent) GetQueueSize() int {
	a.QueueMu.Lock()
	defer a.QueueMu.Unlock()
	return len(a.PreferenceQueue)
}

func (a *Agent) PopBatch(size int) []PreferencePair {
	a.QueueMu.Lock()
	defer a.QueueMu.Unlock()
	if size > len(a.PreferenceQueue) {
		size = len(a.PreferenceQueue)
	}
	batch := make([]PreferencePair, size)
	copy(batch, a.PreferenceQueue[:size])
	a.PreferenceQueue = a.PreferenceQueue[size:]
	return batch
}

// Web crawling methods
func (a *Agent) CrawlWebsite(startURL string, allowedDomains []string) error {
	a.WebCrawler.SetAllowedDomains(allowedDomains)

	pages, err := a.WebCrawler.Crawl(startURL)
	if err != nil {
		return err
	}

	a.CrawledPagesMu.Lock()
	a.CrawledPages = pages
	a.CrawledPagesMu.Unlock()

	log.Printf("Crawled %d pages from %s", len(pages), startURL)
	return nil
}

func (a *Agent) SearchWeb(query string) []string {
	a.CrawledPagesMu.RLock()
	defer a.CrawledPagesMu.RUnlock()

	results := a.WebCrawler.Search(query, a.CrawledPages)
	log.Printf("Web search for '%s' found %d results", query, len(results))
	return results
}

func (a *Agent) GetWebContext(query string) string {
	a.CrawledPagesMu.RLock()
	defer a.CrawledPagesMu.RUnlock()

	if len(a.CrawledPages) == 0 {
		return ""
	}

	results := a.WebCrawler.Search(query, a.CrawledPages)
	if len(results) == 0 {
		return ""
	}

	// Extract text from relevant pages
	var relevantPages []webcrawler.Page
	for _, page := range a.CrawledPages {
		for _, resultURL := range results {
			if page.URL == resultURL {
				relevantPages = append(relevantPages, page)
				break
			}
		}
	}

	return a.WebCrawler.ExtractTextFromPages(relevantPages)
}

func (a *Agent) GenerateWithWebContext(prompt string) (string, error) {
	webContext := a.GetWebContext(prompt)

	if webContext != "" {
		prompt = fmt.Sprintf("Web Context:\n%s\n\nQuestion: %s", webContext, prompt)
	}

	// Placeholder for generation without Ollama dependency.
	// This endpoint remains truth-labeled as a scaffold until wired to the
	// configured model runner.
	return fmt.Sprintf("Generated response for: %s (with web context)", prompt), nil
}
