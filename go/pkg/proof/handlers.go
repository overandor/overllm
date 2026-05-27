package proof

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
)

// Handlers - HTTP handlers for proof API endpoints
type Handlers struct {
	Client *ProofClient
}

// NewHandlers creates new proof handlers
func NewHandlers(proofDaemonURL string) *Handlers {
	return &Handlers{
		Client: NewProofClient(proofDaemonURL),
	}
}

// HandleGenerateReceipt handles POST /api/proof/receipt
func (h *Handlers) HandleGenerateReceipt(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	var req GenerateReceiptRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	receipt, err := h.Client.GenerateReceipt(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(receipt)
}

// HandleGetReceipt handles GET /api/proof/receipt/{id}
func (h *Handlers) HandleGetReceipt(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", http.StatusMethodNotAllowed)
		return
	}

	receiptID := strings.TrimPrefix(r.URL.Path, "/api/proof/receipt/")
	if receiptID == "" {
		http.Error(w, "receipt ID required", http.StatusBadRequest)
		return
	}

	receipt, err := h.Client.GetReceipt(receiptID)
	if err != nil {
		if strings.Contains(err.Error(), "not found") {
			http.Error(w, err.Error(), http.StatusNotFound)
		} else {
			http.Error(w, err.Error(), http.StatusInternalServerError)
		}
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(receipt)
}

// HandleListReceipts handles GET /api/proof/receipts
func (h *Handlers) HandleListReceipts(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", http.StatusMethodNotAllowed)
		return
	}

	sessionID := r.URL.Query().Get("session_id")
	limit := 100
	if limitStr := r.URL.Query().Get("limit"); limitStr != "" {
		fmt.Sscanf(limitStr, "%d", &limit)
	}

	receipts, err := h.Client.ListReceipts(sessionID, limit)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	response := map[string]interface{}{
		"receipts": receipts,
		"total":    len(receipts),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// HandleMemoryMarket handles GET /api/proof/market
func (h *Handlers) HandleMemoryMarket(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", http.StatusMethodNotAllowed)
		return
	}

	stats, err := h.Client.GetMemoryMarket()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(stats)
}

// HandleUploadToIPFS handles POST /api/proof/ipfs/{id}
func (h *Handlers) HandleUploadToIPFS(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	receiptID := strings.TrimPrefix(r.URL.Path, "/api/proof/ipfs/")
	if receiptID == "" {
		http.Error(w, "receipt ID required", http.StatusBadRequest)
		return
	}

	cid, err := h.Client.UploadToIPFS(receiptID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	response := map[string]string{
		"ipfs_cid": cid,
		"message":  "Successfully uploaded to IPFS",
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// HandleAnchorToSolana handles POST /api/proof/solana/{id}
func (h *Handlers) HandleAnchorToSolana(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	receiptID := strings.TrimPrefix(r.URL.Path, "/api/proof/solana/")
	if receiptID == "" {
		http.Error(w, "receipt ID required", http.StatusBadRequest)
		return
	}

	signature, err := h.Client.AnchorToSolana(receiptID)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	response := map[string]string{
		"solana_signature": signature,
		"message":          "Successfully anchored to Solana devnet",
		"explorer_url":     fmt.Sprintf("https://explorer.solana.com/tx/%s?cluster=devnet", signature),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}
