"""
Scraper para sites estáticos usando Scrapy
"""
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response
from bs4 import BeautifulSoup
from typing import Dict, Optional
import multiprocessing
from .config import SCRAPY_SETTINGS


class StaticScraper:
    """Scraper otimizado para sites estáticos usando Scrapy"""
    
    def __init__(self):
        self.result = None
        
    def scrape(self, url: str) -> Dict[str, str]:
        """
        Extrai conteúdo de um site estático
        
        Args:
            url: URL do site a ser extraído
            
        Returns:
            Dicionário com 'title', 'content', 'url', 'html'
            
        Raises:
            Exception: Se houver erro no scraping
        """
        try:
            # Scrapy precisa rodar em processo separado para evitar conflitos
            # com event loop do Flask
            queue = multiprocessing.Queue()
            process = multiprocessing.Process(
                target=self._run_spider,
                args=(url, queue)
            )
            process.start()
            process.join(timeout=15)  # Timeout de 15 segundos
            
            if process.is_alive():
                process.terminate()
                process.join()
                raise Exception("Timeout ao fazer scraping")
            
            if not queue.empty():
                result = queue.get()
                if isinstance(result, Exception):
                    raise result
                return result
            else:
                raise Exception("Nenhum resultado obtido do scraping")
                
        except Exception as e:
            raise Exception(f"Erro no scraping com Scrapy: {str(e)}")
    
    @staticmethod
    def _run_spider(url: str, queue: multiprocessing.Queue):
        """Executa spider Scrapy em processo separado"""
        try:
            class ContentSpider(scrapy.Spider):
                name = 'content_spider'
                start_urls = [url]
                custom_settings = SCRAPY_SETTINGS
                
                def parse(self, response: Response):
                    """Parse da resposta HTTP"""
                    # Tenta detectar encoding ou usar o do response
                    try:
                        html_content = response.text
                    except:
                        # Fallback para latin-1 se utf-8 falhar (comum em sites antigos do governo)
                        html_content = response.body.decode('latin-1', errors='replace')

                    # Usa html.parser para evitar erros de encoding do lxml (bytes 0x81 etc)
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extrai título
                    title = ''
                    title_tag = soup.find('title')
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                    
                    # Se não encontrou título, tenta h1
                    if not title:
                        h1_tag = soup.find('h1')
                        if h1_tag:
                            title = h1_tag.get_text(strip=True)
                    
                    # Extrai conteúdo principal
                    content = ''
                    
                    # Tenta encontrar tag article, main ou section
                    main_content = (
                        soup.find('article') or 
                        soup.find('main') or 
                        soup.find('section', class_='content') or
                        soup.find('div', class_='content') or
                        soup.find('div', id='content') or
                        soup.find('div', id='main')
                    )
                    
                    main_content_html = ''
                    
                    if main_content:
                        # Remove scripts, styles e outros elementos desnecessários
                        for tag in main_content.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                            tag.decompose()
                        
                        # Salva HTML do conteúdo principal para conversão Markdown correta
                        main_content_html = str(main_content)
                        content = main_content.get_text(separator='\n', strip=True)
                    else:
                        # Fallback: pega todo o body
                        body = soup.find('body')
                        if body:
                            for tag in body.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                                tag.decompose()
                            
                            # Salva HTML do body
                            main_content_html = str(body)
                            content = body.get_text(separator='\n', strip=True)
                    
                    # Limpa conteúdo (remove linhas vazias excessivas)
                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                    content = '\n'.join(lines)
                    
                    # Extrai links internos
                    links = []
                    base_url = response.url
                    
                    # Verifica se existe tag <base>
                    base_tag = soup.find('base', href=True)
                    if base_tag:
                        base_url = urljoin(response.url, base_tag['href'])
                    else:
                        # Se URL terminar em .htm/.html/ etc com barra no final, remove a barra
                        if base_url.endswith('/') and any(base_url.lower().rstrip('/').endswith(ext) for ext in ['.htm', '.html', '.asp', '.aspx', '.php']):
                            base_url = base_url.rstrip('/')
                        
                    base_domain = '/'.join(base_url.split('/')[:3])
                    
                    # Extensões ignoradas (arquivos binários)
                    IGNORED_EXTENSIONS = {
                        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
                        '.zip', '.rar', '.7z', '.tar', '.gz', 
                        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
                        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv'
                    }

                    # Padrões ignorados na URL (evita links quebrados comuns de menus antigos)
                    IGNORED_PATTERNS = ['xxla', 'javascript:', 'mailto:', '#']
                    
                    from urllib.parse import urljoin, urlparse
                    import os

                    for a_tag in soup.find_all('a', href=True):
                        href = a_tag['href']
                        
                        # Ignora links vazios ou com padrões ignorados
                        if not href or any(p in href.lower() for p in IGNORED_PATTERNS):
                            continue
                            
                        # Resolve URLs relativas corretamente usando urljoin com a base corrigida
                        # Limpa espaços em branco que podem quebrar a URL
                        full_url = urljoin(base_url, href.strip())
                        
                        # Remove fragmentos
                        full_url = full_url.split('#')[0]

                        # Verifica novamente padrões ignorados na URL completa
                        if any(p in full_url.lower() for p in IGNORED_PATTERNS):
                            continue

                        # Verifica extensão do arquivo
                        try:
                            parsed = urlparse(full_url)
                            path = parsed.path.lower()
                            ext = os.path.splitext(path)[1]
                            if ext in IGNORED_EXTENSIONS:
                                continue
                        except:
                            pass

                        # Adiciona se for do mesmo domínio
                        if base_domain in full_url:
                            links.append(full_url)
                    
                    # Remove duplicatas mantendo ordem
                    links = list(dict.fromkeys(links))

                    result = {
                        'title': title,
                        'content': content,
                        'url': response.url,
                        'html': html_content,
                        'internal_links': links,
                        'main_content_html': main_content_html
                    }
                    
                    queue.put(result)
            
            # Configura e executa o crawler
            process = CrawlerProcess(settings=SCRAPY_SETTINGS)
            process.crawl(ContentSpider)
            process.start()
            
        except Exception as e:
            queue.put(e)
