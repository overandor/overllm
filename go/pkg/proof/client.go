package proof

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// ProofClient - Go client for Rust proof daemon
type ProofClient struct {
	baseURL    string
	httpClient *http.Client
}

// NewProofClient creates a new proof client
func NewProofClient(baseURL string) *ProofClient {
	return &ProofClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GenerateReceiptRequest - Request to generate a coding receipt
type GenerateReceiptRequest struct {
	SessionID   string        `json:"session_id"`
	ActionType  string        `json:"action_type"`
	Prompt      []byte        `json:"prompt"`
	FilesTouched []FileAction `json:"files_touched"`
	CommandsRun []CommandExec `json:"commands_run"`
	Stdout      []byte        `json:"stdout"`
	Stderr      []byte        `json:"stderr"`
	ExitCode    int32         `json:"exit_code"`
	Diff        []byte        `json:"diff"`
	TestResult  []byte        `json:"test_result"`
}

// FileAction - File modification tracking
type FileAction struct {
	Path       string `json:"path"`
	Action     string `json:"action"` // read, write, edit, delete, create
	BeforeHash string `json:"before_hash"`
	AfterHash  string `json:"after_hash"`
}

// CommandExec - Command execution tracking
type CommandExec struct {
	Command    string `json:"command"`
	ExitCode   int32  `json:"exit_code"`
	StdoutHash string `json:"stdout_hash"`
	StderrHash string `json:"stderr_hash"`
	DurationMs uint64 `json:"duration_ms"`
}

// ProofOfTruthCodingReceipt - Complete coding receipt
type ProofOfTruthCodingReceipt struct {
	ReceiptID          string         `json:"receipt_id"`
	SessionID          string         `json:"session_id"`
	PromptHash         string         `json:"prompt_hash"`
	ModelID            string         `json:"model_id"`
	WorkerID           string         `json:"worker_id"`
	FilesTouched       []FileAction   `json:"files_touched"`
	CommandsRun        []CommandExec  `json:"commands_run"`
	StdoutHash         string         `json:"stdout_hash"`
	StderrHash         string         `json:"stderr_hash"`
	ExitCode           int32          `json:"exit_code"`
	DiffHash           string         `json:"diff_hash"`
	TestResultHash     string         `json:"test_result_hash"`
	ProofSignature     string         `json:"proof_signature"`
	MemoryPriceLamports uint64         `json:"memory_price_lamports"`
	CreatedAt          string         `json:"created_at"`
	SolanaTxSignature  *string        `json:"solana_tx_signature"`
}

// MemoryMarketStats - Memory market statistics
type MemoryMarketStats struct {
	TotalLiquidity   uint64 `json:"total_liquidity"`
	TotalReceipts    int    `json:"total_receipts"`
	ActiveSessions   int    `json:"active_sessions"`
	BasePrice        uint64 `json:"base_price"`
	PricingFormula   string `json:"pricing_formula"`
	FloorPrice       uint64 `json:"floor_price"`
	MaxMultiplier    float64 `json:"max_multiplier"`
}

// GenerateReceipt generates a new coding receipt
func (c *ProofClient) GenerateReceipt(req GenerateReceiptRequest) (*ProofOfTruthCodingReceipt, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	resp, err := c.httpClient.Post(
		c.baseURL+"/receipt",
		"application/json",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("proof daemon returned status %d", resp.StatusCode)
	}

	var receipt ProofOfTruthCodingReceipt
	if err := json.NewDecoder(resp.Body).Decode(&receipt); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &receipt, nil
}

// GetReceipt retrieves a receipt by ID
func (c *ProofClient) GetReceipt(receiptID string) (*ProofOfTruthCodingReceipt, error) {
	resp, err := c.httpClient.Get(fmt.Sprintf("%s/receipt/%s", c.baseURL, receiptID))
	if err != nil {
		return nil, fmt.Errorf("failed to get receipt: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("receipt not found")
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("proof daemon returned status %d", resp.StatusCode)
	}

	var receipt ProofOfTruthCodingReceipt
	if err := json.NewDecoder(resp.Body).Decode(&receipt); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &receipt, nil
}

// ListReceipts lists all receipts
func (c *ProofClient) ListReceipts(sessionID string, limit int) ([]ProofOfTruthCodingReceipt, error) {
	url := fmt.Sprintf("%s/receipts?limit=%d", c.baseURL, limit)
	if sessionID != "" {
		url += "&session_id=" + sessionID
	}

	resp, err := c.httpClient.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to list receipts: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("proof daemon returned status %d", resp.StatusCode)
	}

	var response struct {
		Receipts []ProofOfTruthCodingReceipt `json:"receipts"`
		Total    int                          `json:"total"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return response.Receipts, nil
}

// GetMemoryMarket retrieves memory market statistics
func (c *ProofClient) GetMemoryMarket() (*MemoryMarketStats, error) {
	resp, err := c.httpClient.Get(c.baseURL + "/market")
	if err != nil {
		return nil, fmt.Errorf("failed to get memory market: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("proof daemon returned status %d", resp.StatusCode)
	}

	var stats MemoryMarketStats
	if err := json.NewDecoder(resp.Body).Decode(&stats); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return &stats, nil
}

// UploadToIPFS uploads a receipt to IPFS
func (c *ProofClient) UploadToIPFS(receiptID string) (string, error) {
	resp, err := c.httpClient.Post(
		fmt.Sprintf("%s/ipfs/%s", c.baseURL, receiptID),
		"application/json",
		nil,
	)
	if err != nil {
		return "", fmt.Errorf("failed to upload to IPFS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("IPFS upload failed (status %d): %s", resp.StatusCode, string(body))
	}

	var response struct {
		IPFSCid string `json:"ipfs_cid"`
		Error   string `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	if response.Error != "" {
		return "", fmt.Errorf("IPFS upload error: %s", response.Error)
	}

	return response.IPFSCid, nil
}

// AnchorToSolana anchors a receipt to Solana devnet
func (c *ProofClient) AnchorToSolana(receiptID string) (string, error) {
	resp, err := c.httpClient.Post(
		fmt.Sprintf("%s/solana/%s", c.baseURL, receiptID),
		"application/json",
		nil,
	)
	if err != nil {
		return "", fmt.Errorf("failed to anchor to Solana: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Solana anchoring failed (status %d): %s", resp.StatusCode, string(body))
	}

	var response struct {
		Signature string `json:"solana_signature"`
		Error     string `json:"error"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	if response.Error != "" {
		return "", fmt.Errorf("Solana anchoring error: %s", response.Error)
	}

	return response.Signature, nil
}
