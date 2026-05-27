package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/overllm/overllm-agent/pkg/agent"
	"github.com/overllm/overllm-agent/pkg/server"
	"github.com/overllm/overllm-agent/pkg/trainer"
)

func main() {
	fmt.Printf("=== OverLLM Agent ===\n")
	fmt.Printf("Data dir: ~/.overllm/data\n")
	fmt.Printf("Punishment-as-Reward: enabled (DPO training on system context)\n")
	fmt.Printf("\n")
	a := agent.NewAgent()
	a.StartCollector()
	a.OverAgent.Start()
	fmt.Printf("OverAgent: GA population=%d, tick=1s, error-is-reward=ON\n", 20)
	t := trainer.NewDPOTrainer(a, "")
	go t.RunLoop()
	srv := server.New(a, ":7749")
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh
		fmt.Println("\nShutting down...")
		a.Running = false
		os.Exit(0)
	}()
	if err := srv.Run(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
