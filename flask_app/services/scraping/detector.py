"""
Detector de tipo de site (estático vs JavaScript/SPA)
"""
import requests
from bs4 import BeautifulSoup
from .config import REQUEST_TIMEOUT, JS_FRAMEWORK_PATTERNS, CONTENT_TAGS


class SiteDetector:
    """Detecta se um site é estático ou requer JavaScript"""
    
    @staticmethod
    def detect(url: str) -> str:
        """
        Detecta o tipo de site
        
        Args:
            url: URL do site a ser analisado
            
        Returns:
            'static' para sites estáticos, 'dynamic' para sites JavaScript/SPA
            
        Raises:
            Exception: Se houver erro na requisição
        """
        try:
            # Faz requisição HTTP simples
            headers = {
                'User-Agent': 'ADK-Scraper/1.0 (Educational Purpose)'
            }
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            html_content = response.text.lower()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Verifica presença de frameworks JavaScript
            js_score = 0
            for pattern in JS_FRAMEWORK_PATTERNS:
                if pattern.lower() in html_content:
                    js_score += 1
            
            # Se encontrou muitos padrões de frameworks JS, provavelmente é SPA
            if js_score >= 2:
                return 'dynamic'
            
            # Verifica se há conteúdo principal no HTML inicial
            content_found = False
            for tag in CONTENT_TAGS:
                if tag.startswith('.'):
                    # Classe CSS
                    elements = soup.find_all(class_=tag[1:])
                elif tag.startswith('#'):
                    # ID
                    elements = soup.find_all(id=tag[1:])
                else:
                    # Tag HTML
                    elements = soup.find_all(tag)
                
                if elements:
                    # Verifica se tem conteúdo textual significativo
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if len(text) > 100:  # Pelo menos 100 caracteres
                            content_found = True
                            break
                
                if content_found:
                    break
            
            # Se encontrou conteúdo principal, é estático
            if content_found:
                return 'static'
            
            # Se não encontrou conteúdo mas tem muito JavaScript, é dinâmico
            script_tags = soup.find_all('script')
            if len(script_tags) > 5:
                return 'dynamic'
            
            # Por padrão, assume estático (mais rápido)
            return 'static'
            
        except requests.exceptions.Timeout:
            raise Exception(f"Timeout ao acessar {url}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao acessar {url}: {str(e)}")
        except Exception as e:
            raise Exception(f"Erro ao detectar tipo de site: {str(e)}")
