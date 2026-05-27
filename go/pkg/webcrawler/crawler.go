package webcrawler

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"

	"golang.org/x/net/html"
)

type Page struct {
	URL         string
	Title       string
	Content     string
	Links       []string
	TextContent string
	Depth       int
	CrawledAt   time.Time
}

type Crawler struct {
	client         *http.Client
	visited        map[string]bool
	visitedMutex   sync.RWMutex
	maxDepth       int
	maxPages       int
	userAgent      string
	timeout        time.Duration
	allowedDomains []string
}

func NewCrawler(maxDepth, maxPages int) *Crawler {
	return &Crawler{
		client: &http.Client{
			Timeout: 30 * time.Second,
		},
		visited:        make(map[string]bool),
		maxDepth:       maxDepth,
		maxPages:       maxPages,
		userAgent:      "OverLLM-Crawler/1.0",
		timeout:        30 * time.Second,
		allowedDomains: []string{},
	}
}

func (c *Crawler) SetAllowedDomains(domains []string) {
	c.allowedDomains = domains
}

func (c *Crawler) isAllowed(urlStr string) bool {
	if len(c.allowedDomains) == 0 {
		return true
	}

	parsedURL, err := url.Parse(urlStr)
	if err != nil {
		return false
	}

	for _, domain := range c.allowedDomains {
		if strings.HasSuffix(parsedURL.Host, domain) {
			return true
		}
	}

	return false
}

func (c *Crawler) Crawl(startURL string) ([]Page, error) {
	var results []Page
	var resultsMutex sync.Mutex

	var crawl func(url string, depth int)
	crawl = func(url string, depth int) {
		if depth > c.maxDepth || len(results) >= c.maxPages {
			return
		}

		c.visitedMutex.Lock()
		if c.visited[url] {
			c.visitedMutex.Unlock()
			return
		}
		c.visited[url] = true
		c.visitedMutex.Unlock()

		if !c.isAllowed(url) {
			return
		}

		page, err := c.fetchPage(url)
		if err != nil {
			fmt.Printf("Error fetching %s: %v\n", url, err)
			return
		}

		page.Depth = depth
		page.CrawledAt = time.Now()

		resultsMutex.Lock()
		results = append(results, *page)
		resultsMutex.Unlock()

		// Crawl linked pages (limit to 5 per page to avoid explosion)
		if depth < c.maxDepth {
			linkCount := 0
			for _, link := range page.Links {
				if linkCount >= 5 {
					break
				}

				// Make absolute URL
				absURL := c.makeAbsoluteURL(link, url)
				if absURL != "" {
					go crawl(absURL, depth+1)
					linkCount++
				}
			}
		}
	}

	crawl(startURL, 0)

	// Wait for goroutines to finish
	time.Sleep(2 * time.Second)

	return results, nil
}

func (c *Crawler) fetchPage(url string) (*Page, error) {
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		return nil, err
	}

	req.Header.Set("User-Agent", c.userAgent)

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	// Parse HTML
	doc, err := html.Parse(bytes.NewReader(body))
	if err != nil {
		return nil, err
	}

	// Extract title
	var title string
	var findTitle func(*html.Node)
	findTitle = func(n *html.Node) {
		if n.Type == html.ElementNode && n.Data == "title" {
			if n.FirstChild != nil {
				title = n.FirstChild.Data
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			findTitle(c)
		}
	}
	findTitle(doc)

	// Extract links
	var links []string
	var crawlLinks func(*html.Node)
	crawlLinks = func(n *html.Node) {
		if n.Type == html.ElementNode && n.Data == "a" {
			for _, attr := range n.Attr {
				if attr.Key == "href" {
					links = append(links, attr.Val)
					break
				}
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			crawlLinks(c)
		}
	}
	crawlLinks(doc)

	// Extract text content
	var textContent strings.Builder
	var extractText func(*html.Node)
	extractText = func(n *html.Node) {
		if n.Type == html.TextNode {
			textContent.WriteString(n.Data)
			textContent.WriteString(" ")
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			extractText(c)
		}
	}
	extractText(doc)

	return &Page{
		URL:         url,
		Title:       title,
		Content:     string(body),
		Links:       links,
		TextContent: strings.TrimSpace(textContent.String()),
	}, nil
}

func (c *Crawler) makeAbsoluteURL(link, base string) string {
	if strings.HasPrefix(link, "http://") || strings.HasPrefix(link, "https://") {
		return link
	}

	baseURL, err := url.Parse(base)
	if err != nil {
		return ""
	}

	relURL, err := url.Parse(link)
	if err != nil {
		return ""
	}

	absURL := baseURL.ResolveReference(relURL)
	return absURL.String()
}

func (c *Crawler) Search(query string, pages []Page) []string {
	var results []string
	queryLower := strings.ToLower(query)

	for _, page := range pages {
		if strings.Contains(strings.ToLower(page.TextContent), queryLower) ||
			strings.Contains(strings.ToLower(page.Title), queryLower) {
			results = append(results, page.URL)
		}
	}

	return results
}

func (c *Crawler) ExtractTextFromPages(pages []Page) string {
	var builder strings.Builder

	for _, page := range pages {
		builder.WriteString(fmt.Sprintf("URL: %s\n", page.URL))
		builder.WriteString(fmt.Sprintf("Title: %s\n", page.Title))
		builder.WriteString(fmt.Sprintf("Content:\n%s\n\n", page.TextContent))
	}

	return builder.String()
}
