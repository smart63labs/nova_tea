"""
Conversor de HTML para Markdown
"""
import html2text
from datetime import datetime
from typing import Dict
from .config import MARKDOWN_SETTINGS, MAX_FILE_SIZE_MB


class MarkdownConverter:
    """Converte HTML extraído para formato Markdown"""
    
    def __init__(self):
        # Configura conversor html2text
        self.converter = html2text.HTML2Text()
        self.converter.body_width = MARKDOWN_SETTINGS['BODY_WIDTH']
        self.converter.ignore_links = MARKDOWN_SETTINGS['IGNORE_LINKS']
        self.converter.ignore_images = MARKDOWN_SETTINGS['IGNORE_IMAGES']
        self.converter.ignore_emphasis = MARKDOWN_SETTINGS['IGNORE_EMPHASIS']
        self.converter.skip_internal_links = MARKDOWN_SETTINGS['SKIP_INTERNAL_LINKS']
        self.converter.inline_links = MARKDOWN_SETTINGS['INLINE_LINKS']
        self.converter.protect_links = MARKDOWN_SETTINGS['PROTECT_LINKS']
        self.converter.mark_code = MARKDOWN_SETTINGS['MARK_CODE']
    
    def convert(self, scraped_data: Dict[str, str]) -> str:
        """
        Converte dados extraídos para Markdown
        
        Args:
            scraped_data: Dicionário com 'title', 'content', 'url', 'html'
            
        Returns:
            String com conteúdo em formato Markdown
            
        Raises:
            Exception: Se arquivo gerado for muito grande
        """
        try:
            title = scraped_data.get('title', 'Sem Título')
            url = scraped_data.get('url', '')
            content = scraped_data.get('content', '')
            html = scraped_data.get('html', '')
            main_content_html = scraped_data.get('main_content_html', '')
            
            # Cria cabeçalho com metadados
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            header = f"""---
título: {title}
url: {url}
data_extração: {now}
fonte: Web Scraping
---

# {title}

**URL Original**: {url}  
**Data de Extração**: {now}

---

"""
            
            # Converte HTML para Markdown
            # Prioriza HTML do conteúdo principal para manter formatação original
            if main_content_html:
                markdown_content = self.converter.handle(main_content_html)
            elif content and len(content) > 100 and not html:
                # Usa texto extraído apenas se não houver HTML disponível
                markdown_content = content
            else:
                # Fallback: Converte HTML completo
                markdown_content = self.converter.handle(html)
            
            # Monta documento final
            full_markdown = header + markdown_content
            
            # Verifica tamanho do arquivo
            size_mb = len(full_markdown.encode('utf-8')) / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                raise Exception(
                    f"Arquivo muito grande ({size_mb:.2f}MB). "
                    f"Máximo permitido: {MAX_FILE_SIZE_MB}MB"
                )
            
            return full_markdown
            
        except Exception as e:
            raise Exception(f"Erro ao converter para Markdown: {str(e)}")
    
    def generate_filename(self, url: str, title: str) -> str:
        """
        Gera nome de arquivo baseado na URL e título
        
        Args:
            url: URL original
            title: Título do documento
            
        Returns:
            Nome de arquivo sanitizado (sem caracteres especiais)
        """
        import re
        import unicodedata
        from urllib.parse import urlparse
        
        # Tenta usar título primeiro
        if title and title != 'Sem Título':
            filename = title
        else:
            # Usa domínio da URL
            parsed = urlparse(url)
            filename = parsed.netloc.replace('www.', '')
        
        # Normaliza para ASCII (remove acentos e caracteres especiais como º)
        # NFKD decompõe caracteres (ex: é -> e + ´)
        # encode('ascii', 'ignore') remove o que não for ASCII
        try:
            filename = unicodedata.normalize('NFKD', filename) \
                .encode('ascii', 'ignore') \
                .decode('ascii')
        except Exception:
            # Fallback se falhar a normalização
            filename = "documento_extraido"
        
        # Remove caracteres especiais e limita tamanho
        # Mantém apenas letras, números, espaços e hífens
        filename = re.sub(r'[^\w\s-]', '', filename)
        filename = re.sub(r'[-\s]+', '_', filename)
        filename = filename.strip('_').lower()
        
        # Garante que não ficou vazio
        if not filename:
            filename = "documento_extraido"
        
        # Limita a 50 caracteres
        if len(filename) > 50:
            filename = filename[:50]
        
        # Adiciona extensão
        return f"{filename}.md"
