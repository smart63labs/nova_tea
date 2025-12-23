"""
Serviço de scraping híbrido (Scrapy + Playwright)
Extrai conteúdo de URLs e converte para Markdown
"""
from .scraper_factory import ScraperFactory

__all__ = ['ScraperFactory']
