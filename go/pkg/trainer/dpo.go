package trainer

import (
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/overllm/overllm-agent/pkg/agent"
)

type DPOTrainer struct {
	Agent       *agent.Agent
	Beta        float64
	LRLastLayer float64
	BatchSize   int
	VocabPath   string
	Tokenizer   *SimpleTokenizer
}

type SimpleTokenizer struct {
	Vocab   []string
	Stoi    map[string]int
	PadID   int
	UnkID   int
	BosID   int
	EosID   int
}

func NewTokenizer(vocabPath string) (*SimpleTokenizer, error) {
	tok := &SimpleTokenizer{
		Stoi:  make(map[string]int),
		Vocab: []string{"<pad>", "<unk>", "<s>", "</s>"},
	}
	tok.PadID = 0
	tok.UnkID = 1
	tok.BosID = 2
	tok.EosID = 3
	for i, w := range tok.Vocab {
		tok.Stoi[w] = i
	}
	if vocabPath != "" {
		data, err := os.ReadFile(vocabPath)
		if err == nil {
			words := strings.Fields(string(data))
			for _, w := range words {
				if _, ok := tok.Stoi[w]; !ok {
					tok.Stoi[w] = len(tok.Vocab)
					tok.Vocab = append(tok.Vocab, w)
				}
			}
		}
	}
	return tok, nil
}

func (t *SimpleTokenizer) Encode(text string) []int {
	var tokens []int
	tokens = append(tokens, t.BosID)
	var cur string
	for _, c := range text {
		ch := string(c)
		if c == ' ' || c == '\n' || c == '\t' || c == '.' || c == ',' || c == '!' || c == '?' {
			if cur != "" {
				if id, ok := t.Stoi[cur]; ok {
					tokens = append(tokens, id)
				} else {
					tokens = append(tokens, t.UnkID)
				}
				cur = ""
			}
			if id, ok := t.Stoi[ch]; ok {
				tokens = append(tokens, id)
			}
		} else {
			cur += ch
		}
	}
	if cur != "" {
		if id, ok := t.Stoi[cur]; ok {
			tokens = append(tokens, id)
		} else {
			tokens = append(tokens, t.UnkID)
		}
	}
	tokens = append(tokens, t.EosID)
	return tokens
}

func NewDPOTrainer(a *agent.Agent, vocabPath string) *DPOTrainer {
	tok, _ := NewTokenizer(vocabPath)
	return &DPOTrainer{
		Agent:       a,
		Beta:        0.1,
		LRLastLayer: 1e-4,
		BatchSize:   4,
		VocabPath:   vocabPath,
		Tokenizer:   tok,
	}
}

func (t *DPOTrainer) RunLoop() {
	for {
		time.Sleep(60 * time.Second)
		batch := t.Agent.PopBatch(t.BatchSize)
		if len(batch) == 0 {
			continue
		}
		loss := t.TrainBatch(batch)
		fmt.Printf("[DPO] Batch size=%d, avg loss=%.4f\n", len(batch), loss)
		logPath := filepath.Join(t.Agent.DataDir, "training_log.jsonl")
		f, _ := os.OpenFile(logPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
		if f != nil {
			entry := map[string]interface{}{
				"timestamp": time.Now().Unix(),
				"loss":      loss,
				"batch":     len(batch),
			}
			b, _ := json.Marshal(entry)
			f.Write(b)
			f.Write([]byte("\n"))
			f.Close()
		}
	}
}

func (t *DPOTrainer) TrainBatch(batch []agent.PreferencePair) float64 {
	totalLoss := 0.0
	for _, pair := range batch {
		chosenTok := t.Tokenizer.Encode(pair.Chosen)
		rejectedTok := t.Tokenizer.Encode(pair.Rejected)
		chosenLogProb := t.approximateLogProb(chosenTok)
		rejectedLogProb := t.approximateLogProb(rejectedTok)
		margin := t.Beta * (chosenLogProb - rejectedLogProb)
		sigmoid := 1.0 / (1.0 + math.Exp(-margin))
		loss := -math.Log(sigmoid + 1e-10)
		totalLoss += loss
		t.writeGradientFile(pair, chosenTok, rejectedTok)
	}
	return totalLoss / float64(len(batch))
}

func (t *DPOTrainer) approximateLogProb(tokens []int) float64 {
	if len(tokens) <= 2 {
		return -1.0
	}
	unique := make(map[int]bool)
	for _, t := range tokens {
		unique[t] = true
	}
	diversity := float64(len(unique)) / float64(len(tokens))
	return -float64(len(tokens)) * 0.05 * diversity
}

func (t *DPOTrainer) writeGradientFile(pair agent.PreferencePair, chosen, rejected []int) {
	gradPath := filepath.Join(t.Agent.DataDir, "gradients")
	os.MkdirAll(gradPath, 0755)
	fname := fmt.Sprintf("grad_%d.bin", time.Now().UnixNano())
	path := filepath.Join(gradPath, fname)
	f, err := os.Create(path)
	if err != nil {
		return
	}
	defer f.Close()
	header := make([]byte, 8)
	header[0] = byte(len(chosen) >> 24)
	header[1] = byte(len(chosen) >> 16)
	header[2] = byte(len(chosen) >> 8)
	header[3] = byte(len(chosen))
	header[4] = byte(len(rejected) >> 24)
	header[5] = byte(len(rejected) >> 16)
	header[6] = byte(len(rejected) >> 8)
	header[7] = byte(len(rejected))
	f.Write(header)
	for _, t := range chosen {
		f.Write([]byte{byte(t >> 24), byte(t >> 16), byte(t >> 8), byte(t)})
	}
	for _, t := range rejected {
		f.Write([]byte{byte(t >> 24), byte(t >> 16), byte(t >> 8), byte(t)})
	}
}
