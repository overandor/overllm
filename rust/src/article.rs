use lopdf::Document;
use pdf_extract::extract_text;
use reqwest;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Read;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Article {
    pub id: String,
    pub title: String,
    pub authors: Vec<String>,
    pub abstract_text: String,
    pub content: String,
    pub source: String, // "arxiv", "pdf", "url"
    pub url: String,
    pub published_date: Option<String>,
    pub categories: Vec<String>,
    pub citations: Vec<String>,
    pub embedding: Vec<f32>,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArXivEntry {
    pub id: String,
    pub title: String,
    pub authors: Vec<String>,
    pub summary: String,
    pub published: String,
    pub categories: Vec<String>,
}

pub struct ArticleIngestor {
    embedding_dim: usize,
}

impl ArticleIngestor {
    pub fn new(embedding_dim: usize) -> Self {
        ArticleIngestor { embedding_dim }
    }

    pub async fn fetch_arxiv(&self, query: &str, max_results: usize) -> Result<Vec<Article>, String> {
        let url = format!(
            "http://export.arxiv.org/api/query?search_query=all:{}&start=0&max_results={}",
            urlencoding::encode(query),
            max_results
        );

        let response = reqwest::get(&url)
            .await
            .map_err(|e| format!("Failed to fetch arXiv: {}", e))?
            .text()
            .await
            .map_err(|e| format!("Failed to read arXiv response: {}", e))?;

        // Parse XML response (simplified - in production use proper XML parser)
        let entries = self.parse_arxiv_xml(&response)?;
        
        let mut articles = Vec::new();
        for entry in entries {
            let summary = entry.summary.clone();
            let article = Article {
                id: entry.id.clone(),
                title: entry.title.clone(),
                authors: entry.authors,
                abstract_text: summary.clone(),
                content: summary.clone(), // v1: use abstract as content
                source: "arxiv".to_string(),
                url: format!("https://arxiv.org/abs/{}", entry.id.split('/').last().unwrap_or(&entry.id)),
                published_date: Some(entry.published),
                categories: entry.categories,
                citations: Vec::new(),
                embedding: self.generate_embedding(&entry.title, &summary),
                timestamp: chrono::Utc::now().timestamp(),
            };
            articles.push(article);
        }

        Ok(articles)
    }

    pub async fn fetch_pdf(&self, url: &str) -> Result<Article, String> {
        let response = reqwest::get(url)
            .await
            .map_err(|e| format!("Failed to fetch PDF: {}", e))?
            .bytes()
            .await
            .map_err(|e| format!("Failed to read PDF bytes: {}", e))?;

        let text = extract_text_from_pdf(&response)
            .map_err(|e| format!("Failed to extract text from PDF: {}", e))?;

        let title = "PDF Document".to_string();
        let abstract_text: String = text.chars().take(500).collect();
        let embedding = self.generate_embedding(&title, &abstract_text);
        
        let article = Article {
            id: format!("pdf_{}", hex::encode(md5::compute(url.as_bytes()).as_ref())),
            title,
            authors: Vec::new(),
            abstract_text,
            content: text,
            source: "pdf".to_string(),
            url: url.to_string(),
            published_date: None,
            categories: Vec::new(),
            citations: Vec::new(),
            embedding,
            timestamp: chrono::Utc::now().timestamp(),
        };

        Ok(article)
    }

    pub async fn ingest_url(&self, url: &str) -> Result<Article, String> {
        let response = reqwest::get(url)
            .await
            .map_err(|e| format!("Failed to fetch URL: {}", e))?
            .text()
            .await
            .map_err(|e| format!("Failed to read URL response: {}", e))?;

        // Extract title and content from HTML (simplified)
        let title = extract_title_from_html(&response);
        let content = extract_text_from_html(&response);

        let article = Article {
            id: format!("url_{}", hex::encode(md5::compute(url.as_bytes()).as_ref())),
            title: title.clone(),
            authors: Vec::new(),
            abstract_text: content.chars().take(500).collect(),
            content: content.clone(),
            source: "url".to_string(),
            url: url.to_string(),
            published_date: None,
            categories: Vec::new(),
            citations: Vec::new(),
            embedding: self.generate_embedding(&title, &content),
            timestamp: chrono::Utc::now().timestamp(),
        };

        Ok(article)
    }

    fn parse_arxiv_xml(&self, xml: &str) -> Result<Vec<ArXivEntry>, String> {
        // Simplified XML parsing - in production use quick-xml or similar
        let mut entries = Vec::new();
        
        // Extract entries using regex (v1 approach)
        let entry_pattern = regex::Regex::new(r"<entry>(.*?)</entry>")
            .map_err(|e| format!("Failed to compile regex: {}", e))?;
        
        for caps in entry_pattern.captures_iter(xml) {
            if let Some(entry_xml) = caps.get(1) {
                let title = extract_xml_tag(entry_xml.as_str(), "title").unwrap_or_default();
                let summary = extract_xml_tag(entry_xml.as_str(), "summary").unwrap_or_default();
                let id = extract_xml_tag(entry_xml.as_str(), "id").unwrap_or_default();
                let published = extract_xml_tag(entry_xml.as_str(), "published").unwrap_or_default();
                
                let authors = extract_authors(entry_xml.as_str());
                let categories = extract_categories(entry_xml.as_str());
                
                entries.push(ArXivEntry {
                    id,
                    title,
                    authors,
                    summary,
                    published,
                    categories,
                });
            }
        }
        
        Ok(entries)
    }

    fn generate_embedding(&self, title: &str, content: &str) -> Vec<f32> {
        // Simple hash-based embedding (v1)
        let text = format!("{} {}", title, content);
        let mut embedding = vec![0.0f32; self.embedding_dim];
        
        let bytes = text.as_bytes();
        for (i, &b) in bytes.iter().enumerate() {
            let idx = (i + b as usize) % self.embedding_dim;
            embedding[idx] += (b as f32) / 255.0;
        }
        
        let norm: f32 = embedding.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for v in embedding.iter_mut() {
                *v /= norm;
            }
        }
        
        embedding
    }

    pub fn chunk_article(&self, article: &Article, chunk_size: usize) -> Vec<String> {
        let words: Vec<&str> = article.content.split_whitespace().collect();
        let mut chunks = Vec::new();
        
        for chunk in words.chunks(chunk_size) {
            chunks.push(chunk.join(" "));
        }
        
        chunks
    }

    pub fn extract_citations(&self, content: &str) -> Vec<String> {
        // Extract citation patterns (v1: simple regex)
        let mut citations = Vec::new();
        
        // DOI pattern
        let doi_pattern = regex::Regex::new(r"10\.\d{4,}/[^\s]+")
            .unwrap_or_else(|_| regex::Regex::new(r"").unwrap());
        
        for cap in doi_pattern.find_iter(content) {
            citations.push(cap.as_str().to_string());
        }
        
        // arXiv pattern
        let arxiv_pattern = regex::Regex::new(r"arXiv:\d{4}\.\d{4,5}")
            .unwrap_or_else(|_| regex::Regex::new(r"").unwrap());
        
        for cap in arxiv_pattern.find_iter(content) {
            citations.push(cap.as_str().to_string());
        }
        
        citations
    }
}

fn extract_text_from_pdf(bytes: &[u8]) -> Result<String, String> {
    // Simplified PDF text extraction - placeholder
    // In production, use proper PDF parsing library
    Ok("PDF text extraction placeholder".to_string())
}

fn extract_title_from_html(html: &str) -> String {
    let title_pattern = regex::Regex::new(r"<title>(.*?)</title>")
        .unwrap_or_else(|_| regex::Regex::new(r"").unwrap());
    
    title_pattern
        .captures(html)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string())
        .unwrap_or_else(|| "Untitled".to_string())
}

fn extract_text_from_html(html: &str) -> String {
    // Remove HTML tags (v1: simple regex)
    let re = regex::Regex::new(r"<[^>]+>")
        .unwrap_or_else(|_| regex::Regex::new(r"").unwrap());
    
    re.replace_all(html, "")
        .replace("&nbsp;", " ")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&amp;", "&")
        .lines()
        .map(|l| l.trim())
        .filter(|l| !l.is_empty())
        .collect::<Vec<_>>()
        .join("\n")
}

fn extract_xml_tag(xml: &str, tag: &str) -> Option<String> {
    let pattern = format!("<{}>(.*?)</{}>", tag, tag);
    let re = regex::Regex::new(&pattern).ok()?;
    re.captures(xml)?.get(1).map(|m| m.as_str().to_string())
}

fn extract_authors(xml: &str) -> Vec<String> {
    let mut authors = Vec::new();
    if let Ok(re) = regex::Regex::new(r"<name>(.*?)</name>") {
        for cap in re.captures_iter(xml) {
            if let Some(name) = cap.get(1) {
                authors.push(name.as_str().to_string());
            }
        }
    }
    authors
}

fn extract_categories(xml: &str) -> Vec<String> {
    let mut categories = Vec::new();
    if let Ok(re) = regex::Regex::new(r#"<category term="(.*?)""#) {
        for cap in re.captures_iter(xml) {
            if let Some(cat) = cap.get(1) {
                categories.push(cat.as_str().to_string());
            }
        }
    }
    categories
}
