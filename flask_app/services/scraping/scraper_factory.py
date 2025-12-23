"""
Factory para seleção e execução de scrapers
"""
from typing import Dict, Tuple
from .detector import SiteDetector
from .scrapy_scraper import StaticScraper
from .playwright_scraper import PlaywrightScraper
from .markdown_converter import MarkdownConverter
import logging


class ScraperFactory:
    """Factory pattern para orquestrar processo de scraping"""
    
    def __init__(self):
        self.detector = SiteDetector()
        self.static_scraper = StaticScraper()
        self.playwright_scraper = PlaywrightScraper()
        self.markdown_converter = MarkdownConverter()
        self.logger = logging.getLogger(__name__)
    
    def scrape_url(self, url: str, force_type: str = None) -> Tuple[str, str, str, list]:
        """
        Executa scraping completo de uma URL
        
        Args:
            url: URL a ser processada
            force_type: Força uso de scraper específico ('static' ou 'dynamic')
                       Se None, detecta automaticamente
            
        Returns:
            Tupla (markdown_content, filename, scraper_type, internal_links)
            
        Raises:
            Exception: Se houver erro em qualquer etapa
        """
        try:
            # 1. Detecta tipo de site (se não forçado)
            if force_type:
                site_type = force_type
                self.logger.info(f"Tipo de scraper forçado: {site_type}")
            else:
                self.logger.info(f"Detectando tipo de site: {url}")
                site_type = self.detector.detect(url)
                self.logger.info(f"Site detectado como: {site_type}")
            
            # 2. Seleciona e executa scraper apropriado
            scraped_data = None
            
            if site_type == 'static':
                # Tenta Scrapy primeiro (mais rápido)
                try:
                    self.logger.info(f"Usando Scrapy para: {url}")
                    scraped_data = self.static_scraper.scrape(url)
                except Exception as e:
                    self.logger.warning(f"Scrapy falhou, tentando Playwright: {str(e)}")
                    # Fallback para Playwright
                    site_type = 'dynamic'
            
            if site_type == 'dynamic' or scraped_data is None:
                self.logger.info(f"Usando Playwright para: {url}")
                scraped_data = self.playwright_scraper.scrape(url)
            
            # Verifica se obteve dados
            if not scraped_data or not scraped_data.get('content'):
                raise Exception("Nenhum conteúdo extraído do site")
            
            # 3. Converte para Markdown
            self.logger.info(f"Convertendo para Markdown: {url}")
            markdown_content = self.markdown_converter.convert(scraped_data)
            
            # 4. Gera nome de arquivo
            filename = self.markdown_converter.generate_filename(
                scraped_data.get('url', url),
                scraped_data.get('title', '')
            )
            
            self.logger.info(f"Scraping concluído: {filename}")
            
            # Recupera links internos se disponíveis
            internal_links = scraped_data.get('internal_links', [])
            
            return markdown_content, filename, site_type, internal_links
            
        except Exception as e:
            self.logger.error(f"Erro no scraping de {url}: {str(e)}")
            raise Exception(f"Falha no scraping: {str(e)}")
    
    def scrape_multiple(self, urls: list) -> Dict[str, Dict]:
        """
        Processa múltiplas URLs
        
        Args:
            urls: Lista de URLs a serem processadas
            
        Returns:
            Dicionário com resultados de cada URL
            {
                'url1': {
                    'status': 'success' | 'error',
                    'markdown': '...',
                    'filename': '...',
                    'scraper_type': 'static' | 'dynamic',
                    'error': '...' (se status == 'error')
                }
            }
        """
        results = {}
        
        for url in urls:
            try:
                markdown, filename, scraper_type = self.scrape_url(url)
                results[url] = {
                    'status': 'success',
                    'markdown': markdown,
                    'filename': filename,
                    'scraper_type': scraper_type
                }
            except Exception as e:
                results[url] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
