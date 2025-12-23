"""
Scraper para sites JavaScript/SPA usando Playwright
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import Dict
from .config import PLAYWRIGHT_SETTINGS


class PlaywrightScraper:
    """Scraper para sites que requerem JavaScript usando Playwright"""
    
    def scrape(self, url: str) -> Dict[str, str]:
        """
        Extrai conteúdo de um site JavaScript/SPA
        
        Args:
            url: URL do site a ser extraído
            
        Returns:
            Dicionário com 'title', 'content', 'url', 'html'
            
        Raises:
            Exception: Se houver erro no scraping
        """
        try:
            with sync_playwright() as p:
                # Inicia navegador em modo headless
                browser = p.chromium.launch(headless=PLAYWRIGHT_SETTINGS['HEADLESS'])
                
                # Cria contexto com viewport configurado
                context = browser.new_context(
                    viewport=PLAYWRIGHT_SETTINGS['VIEWPORT'],
                    ignore_https_errors=True
                )
                
                # Cria nova página
                page = context.new_page()
                
                try:
                    # Navega para URL e aguarda carregamento
                    page.goto(
                        url,
                        wait_until=PLAYWRIGHT_SETTINGS['WAIT_UNTIL'],
                        timeout=PLAYWRIGHT_SETTINGS['TIMEOUT']
                    )
                    
                    # Aguarda um pouco mais para garantir que JavaScript executou
                    page.wait_for_timeout(2000)  # 2 segundos
                    
                    # Extrai título
                    title = page.title()
                    
                    # Extrai HTML completo após renderização JavaScript
                    html = page.content()
                    
                    # Extrai URL final (pode ter havido redirecionamento)
                    final_url = page.url
                    
                    # Parse do HTML com BeautifulSoup
                    # Playwright retorna string Unicode, então não precisamos decodificar
                    # Usamos html.parser que é mais leniente com erros de encoding do que lxml
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Extrai conteúdo principal
                    content = ''
                    
                    # Tenta encontrar tag article, main ou section
                    main_content = (
                        soup.find('article') or 
                        soup.find('main') or 
                        soup.find('section', class_='content') or
                        soup.find('div', class_='content') or
                        soup.find('div', id='content') or
                        soup.find('div', id='main') or
                        soup.find('div', class_='post') or
                        soup.find('div', class_='article')
                    )
                    
                    main_content_html = ''
                    
                    if main_content:
                        # Remove scripts, styles e outros elementos desnecessários
                        for tag in main_content.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                            tag.decompose()
                        
                        # Salva HTML do conteúdo principal para conversão Markdown correta
                        main_content_html = str(main_content)
                        content = main_content.get_text(separator='\n', strip=True)
                    else:
                        # Fallback: pega todo o body
                        body = soup.find('body')
                        if body:
                            for tag in body.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe']):
                                tag.decompose()
                            
                            # Salva HTML do body
                            main_content_html = str(body)
                            content = body.get_text(separator='\n', strip=True)
                    
                    # Limpa conteúdo (remove linhas vazias excessivas)
                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                    content = '\n'.join(lines)
                    
                    # Extrai links internos
                    links = []
                    
                    # Verifica se existe tag <base>
                    base_url = final_url
                    base_tag = soup.find('base', href=True)
                    if base_tag:
                        base_url = urljoin(final_url, base_tag['href'])
                    else:
                        # Correção da URL base se terminar com barra indevidamente
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
                        'url': final_url,
                        'html': html,
                        'internal_links': links,
                        'main_content_html': main_content_html
                    }
                    
                    return result
                    
                except PlaywrightTimeout:
                    raise Exception(f"Timeout ao carregar {url}")
                    
                finally:
                    # Fecha página e navegador
                    page.close()
                    context.close()
                    browser.close()
                    
        except Exception as e:
            raise Exception(f"Erro no scraping com Playwright: {str(e)}")
