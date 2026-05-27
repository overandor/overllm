module github.com/overllm/overllm-agent

go 1.26

require github.com/overllm/overllm-agent/pkg/webcrawler v0.0.0

require golang.org/x/net v0.17.0 // indirect

replace github.com/overllm/overllm-agent/pkg/webcrawler => ./pkg/webcrawler
