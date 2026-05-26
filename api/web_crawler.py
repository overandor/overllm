"""
OverLLM Web Crawler with Iframe Vision
Crawls websites, renders them in iframes, extracts visual and text data for training
"""

import asyncio
import aiohttp
import json
import time
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import hashlib
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CrawledPage:
    """Data structure for a crawled webpage"""
    url: str
    title: str
    text_content: str
    html_content: str
    visual_data: Dict
    links: List[str]
    images: List[str]
    metadata: Dict
    timestamp: float
    content_hash: str
    screenshot_data: Optional[str] = None
    iframe_render_data: Optional[Dict] = None


@dataclass
class CrawlerConfig:
    """Crawler configuration"""
    max_pages_per_domain: int = 50
    max_depth: int = 3
    follow_external_links: bool = False
    allowed_domains: Set[str] = None
    blocked_domains: Set[str] = None
    user_agent: str = "Mozilla/5.0 (compatible; OverLLM-Crawler/1.0; +https://overllm.ai/bot)"
    request_timeout: int = 30
    concurrent_requests: int = 5
    respect_robots_txt: bool = True
    min_content_length: int = 100
    max_content_length: int = 1000000


class IframeVisionRenderer:
    """Renders webpages in iframe-like environments for vision extraction"""
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.render_cache: Dict[str, Dict] = {}
        
    async def start(self):
        """Start the rendering session"""
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': CrawlerConfig().user_agent}
        )
        
    async def stop(self):
        """Stop the rendering session"""
        if self.session:
            await self.session.close()
            
    async def render_page(self, url: str) -> Dict:
        """Render a page and extract visual data"""
        if url in self.render_cache:
            return self.render_cache[url]
            
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Parse HTML
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extract visual layout information
                    visual_data = {
                        'layout_structure': self.extract_layout_structure(soup),
                        'color_scheme': self.extract_color_scheme(soup),
                        'typography': self.extract_typography(soup),
                        'media_elements': self.extract_media_info(soup),
                        'interactive_elements': self.extract_interactive_elements(soup),
                        'content_density': self.calculate_content_density(soup, html),
                        'readability_score': self.calculate_readability(html),
                        'viewport_meta': self.extract_viewport_meta(soup)
                    }
                    
                    self.render_cache[url] = visual_data
                    return visual_data
                    
        except Exception as e:
            logger.error(f"Error rendering page {url}: {e}")
            return {}
            
    def extract_layout_structure(self, soup: BeautifulSoup) -> Dict:
        """Extract the layout structure of the page"""
        structure = {
            'header_count': len(soup.find_all('header')),
            'nav_count': len(soup.find_all('nav')),
            'main_count': len(soup.find_all('main')),
            'section_count': len(soup.find_all('section')),
            'article_count': len(soup.find_all('article')),
            'aside_count': len(soup.find_all('aside')),
            'footer_count': len(soup.find_all('footer')),
            'div_count': len(soup.find_all('div')),
            'total_elements': len(soup.find_all()),
            'nesting_depth': self.calculate_max_depth(soup)
        }
        return structure
        
    def calculate_max_depth(self, soup: BeautifulSoup) -> int:
        """Calculate maximum nesting depth"""
        def get_depth(element, current_depth=0):
            if not element.children:
                return current_depth
            return max(get_depth(child, current_depth + 1) for child in element.children 
                       if hasattr(child, 'children'))
        return get_depth(soup)
        
    def extract_color_scheme(self, soup: BeautifulSoup) -> Dict:
        """Extract color information from CSS"""
        colors = {
            'background_colors': set(),
            'text_colors': set(),
            'accent_colors': set()
        }
        
        # Extract from style tags
        for style in soup.find_all('style'):
            style_text = style.get_text()
            # Simple regex to extract hex colors
            hex_colors = re.findall(r'#[0-9a-fA-F]{6}', style_text)
            colors['background_colors'].update(hex_colors)
            
        # Extract from inline styles
        for element in soup.find_all(style=True):
            style_text = element.get('style', '')
            hex_colors = re.findall(r'#[0-9a-fA-F]{6}', style_text)
            colors['background_colors'].update(hex_colors)
            
        return {
            'background_colors': list(colors['background_colors'])[:10],
            'text_colors': list(colors['text_colors'])[:10],
            'accent_colors': list(colors['accent_colors'])[:10],
            'total_unique_colors': len(colors['background_colors'] | colors['text_colors'] | colors['accent_colors'])
        }
        
    def extract_typography(self, soup: BeautifulSoup) -> Dict:
        """Extract typography information"""
        fonts = set()
        font_sizes = []
        
        for element in soup.find_all(style=True):
            style_text = element.get('style', '')
            font_match = re.search(r'font-family:\s*([^;]+)', style_text)
            if font_match:
                fonts.add(font_match.group(1).strip())
            size_match = re.search(r'font-size:\s*([^;]+)', style_text)
            if size_match:
                font_sizes.append(size_match.group(1).strip())
                
        return {
            'unique_fonts': list(fonts)[:5],
            'font_size_samples': font_sizes[:10],
            'total_font_variations': len(fonts)
        }
        
    def extract_media_info(self, soup: BeautifulSoup) -> Dict:
        """Extract media element information"""
        images = soup.find_all('img')
        videos = soup.find_all('video')
        audios = soup.find_all('audio')
        
        return {
            'image_count': len(images),
            'video_count': len(videos),
            'audio_count': len(audios),
            'total_media_size': sum(len(img.get('src', '')) for img in images),
            'has_lazy_loading': any(img.get('loading') == 'lazy' for img in images)
        }
        
    def extract_interactive_elements(self, soup: BeautifulSoup) -> Dict:
        """Extract interactive element information"""
        buttons = soup.find_all('button')
        forms = soup.find_all('form')
        inputs = soup.find_all('input')
        links = soup.find_all('a')
        
        return {
            'button_count': len(buttons),
            'form_count': len(forms),
            'input_count': len(inputs),
            'link_count': len(links),
            'has_javascript': bool(soup.find_all('script')),
            'script_count': len(soup.find_all('script'))
        }
        
    def calculate_content_density(self, soup: BeautifulSoup, html: str) -> Dict:
        """Calculate content density metrics"""
        text = soup.get_text()
        text_length = len(text)
        html_length = len(html)
        
        return {
            'text_to_html_ratio': text_length / html_length if html_length > 0 else 0,
            'text_length': text_length,
            'html_length': html_length,
            'word_count': len(text.split()),
            'paragraph_count': len(soup.find_all('p'))
        }
        
    def calculate_readability(self, html: str) -> Dict:
        """Calculate readability metrics"""
        text = BeautifulSoup(html, 'html.parser').get_text()
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        if len(sentences) == 0:
            return {'avg_sentence_length': 0, 'avg_word_length': 0}
            
        avg_sentence_length = len(words) / len(sentences) if len(sentences) > 0 else 0
        avg_word_length = sum(len(word) for word in words) / len(words) if len(words) > 0 else 0
        
        return {
            'avg_sentence_length': avg_sentence_length,
            'avg_word_length': avg_word_length,
            'total_words': len(words),
            'total_sentences': len(sentences)
        }
        
    def extract_viewport_meta(self, soup: BeautifulSoup) -> Dict:
        """Extract viewport meta information"""
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        return {
            'has_viewport': viewport is not None,
            'viewport_content': viewport.get('content', '') if viewport else ''
        }


class WebCrawler:
    """Main web crawler with iframe vision capabilities"""
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        self.renderer = IframeVisionRenderer()
        self.crawled_urls: Set[str] = set()
        self.crawled_pages: List[CrawledPage] = []
        self.domain_page_counts: Dict[str, int] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_crawling = False
        
    async def start(self):
        """Start the crawler"""
        await self.renderer.start()
        self.session = aiohttp.ClientSession(
            headers={'User-Agent': self.config.user_agent}
        )
        
    async def stop(self):
        """Stop the crawler"""
        self.is_crawling = False
        await self.renderer.stop()
        if self.session:
            await self.session.close()
            
    async def crawl_url(self, url: str, depth: int = 0) -> Optional[CrawledPage]:
        """Crawl a single URL with iframe vision"""
        if depth > self.config.max_depth:
            return None
            
        if url in self.crawled_urls:
            return None
            
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Check domain limits
        if self.domain_page_counts.get(domain, 0) >= self.config.max_pages_per_domain:
            logger.info(f"Domain limit reached for {domain}")
            return None
            
        # Check blocked domains
        if self.config.blocked_domains and domain in self.config.blocked_domains:
            logger.info(f"Domain blocked: {domain}")
            return None
            
        # Check allowed domains
        if self.config.allowed_domains and domain not in self.config.allowed_domains:
            if not self.config.follow_external_links:
                return None
                
        try:
            logger.info(f"Crawling: {url} (depth: {depth})")
            
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)) as response:
                if response.status != 200:
                    logger.warning(f"Failed to crawl {url}: HTTP {response.status}")
                    return None
                    
                html = await response.text()
                
                # Check content length
                if len(html) < self.config.min_content_length:
                    logger.warning(f"Content too short: {url}")
                    return None
                    
                if len(html) > self.config.max_content_length:
                    logger.warning(f"Content too long: {url}")
                    return None
                    
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract page data
                title = soup.title.string if soup.title else ""
                text_content = soup.get_text()
                
                # Extract links
                links = []
                for link in soup.find_all('a', href=True):
                    absolute_url = urljoin(url, link['href'])
                    if self.is_valid_url(absolute_url):
                        links.append(absolute_url)
                        
                # Extract images
                images = []
                for img in soup.find_all('img', src=True):
                    absolute_url = urljoin(url, img['src'])
                    images.append(absolute_url)
                    
                # Extract metadata
                metadata = {
                    'description': soup.find('meta', attrs={'name': 'description'}).get('content', '') if soup.find('meta', attrs={'name': 'description'}) else '',
                    'keywords': soup.find('meta', attrs={'name': 'keywords'}).get('content', '') if soup.find('meta', attrs={'name': 'keywords'}) else '',
                    'author': soup.find('meta', attrs={'name': 'author'}).get('content', '') if soup.find('meta', attrs={'name': 'author'}) else '',
                    'language': soup.find('html').get('lang', '') if soup.find('html') else ''
                }
                
                # Render with iframe vision
                visual_data = await self.renderer.render_page(url)
                
                # Create content hash
                content_hash = hashlib.sha256(html.encode()).hexdigest()[:16]
                
                # Create crawled page
                page = CrawledPage(
                    url=url,
                    title=title,
                    text_content=text_content,
                    html_content=html,
                    visual_data=visual_data,
                    links=links,
                    images=images,
                    metadata=metadata,
                    timestamp=time.time(),
                    content_hash=content_hash,
                    iframe_render_data=visual_data
                )
                
                # Update tracking
                self.crawled_urls.add(url)
                self.crawled_pages.append(page)
                self.domain_page_counts[domain] = self.domain_page_counts.get(domain, 0) + 1
                
                logger.info(f"Successfully crawled: {url} (total: {len(self.crawled_pages)})")
                
                # Recursively crawl links
                if depth < self.config.max_depth:
                    for link in links[:10]:  # Limit to 10 links per page
                        if link not in self.crawled_urls:
                            await self.crawl_url(link, depth + 1)
                            
                return page
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout crawling {url}")
            return None
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None
            
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid for crawling"""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except:
            return False
            
    async def crawl_seed_urls(self, seed_urls: List[str]) -> List[CrawledPage]:
        """Crawl starting from seed URLs"""
        self.is_crawling = True
        results = []
        
        try:
            tasks = [self.crawl_url(url) for url in seed_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None and exceptions
            valid_results = [r for r in results if r and not isinstance(r, Exception)]
            
        except Exception as e:
            logger.error(f"Error in crawl_seed_urls: {e}")
        finally:
            self.is_crawling = False
            
        return valid_results
        
    def get_training_data(self) -> List[Dict]:
        """Convert crawled pages to training data format"""
        training_data = []
        
        for page in self.crawled_pages:
            # Create training sample from page
            sample = {
                'text': page.text_content,
                'metadata': {
                    'url': page.url,
                    'title': page.title,
                    'domain': urlparse(page.url).netloc,
                    'timestamp': page.timestamp,
                    'content_hash': page.content_hash
                },
                'visual_features': page.visual_data,
                'labels': {
                    'content_type': self.classify_content_type(page),
                    'quality_score': self.calculate_quality_score(page),
                    'training_value': self.calculate_training_value(page)
                }
            }
            training_data.append(sample)
            
        return training_data
        
    def classify_content_type(self, page: CrawledPage) -> str:
        """Classify the content type of a page"""
        text = page.text_content.lower()
        
        if any(word in text for word in ['blog', 'article', 'post']):
            return 'blog'
        elif any(word in text for word in ['documentation', 'docs', 'tutorial']):
            return 'documentation'
        elif any(word in text for word in ['news', 'article', 'story']):
            return 'news'
        elif any(word in text for word in ['product', 'shop', 'buy']):
            return 'ecommerce'
        else:
            return 'general'
            
    def calculate_quality_score(self, page: CrawledPage) -> float:
        """Calculate quality score for training"""
        score = 0.5
        
        # Text length factor
        text_length = len(page.text_content)
        if text_length > 1000:
            score += 0.2
        elif text_length > 500:
            score += 0.1
            
        # Visual structure factor
        if page.visual_data.get('layout_structure', {}).get('total_elements', 0) > 50:
            score += 0.1
            
        # Content density factor
        density = page.visual_data.get('content_density', {}).get('text_to_html_ratio', 0)
        if density > 0.3:
            score += 0.1
            
        # Metadata factor
        if page.metadata.get('description'):
            score += 0.1
            
        return min(1.0, score)
        
    def calculate_training_value(self, page: CrawledPage) -> float:
        """Calculate training value based on various factors"""
        value = 0.5
        
        # Domain authority (simplified)
        domain = urlparse(page.url).netloc
        if any(trusted in domain for trusted in ['github', 'stackoverflow', 'wikipedia', 'docs']):
            value += 0.3
            
        # Content uniqueness
        if page.content_hash:
            value += 0.1
            
        # Visual complexity
        visual_complexity = page.visual_data.get('layout_structure', {}).get('total_elements', 0)
        if visual_complexity > 100:
            value += 0.1
            
        return min(1.0, value)
        
    def get_crawl_stats(self) -> Dict:
        """Get crawling statistics"""
        return {
            'total_pages_crawled': len(self.crawled_pages),
            'unique_urls': len(self.crawled_urls),
            'domains_crawled': len(self.domain_page_counts),
            'domain_breakdown': self.domain_page_counts,
            'is_crawling': self.is_crawling,
            'avg_page_size': sum(len(p.html_content) for p in self.crawled_pages) / len(self.crawled_pages) if self.crawled_pages else 0
        }


# Global crawler instance
crawler = WebCrawler()


async def start_crawler_server():
    """Start the crawler server"""
    await crawler.start()
    logger.info("Web crawler server started")
    
    # Keep running
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(start_crawler_server())