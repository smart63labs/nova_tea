
from urllib.parse import urljoin, urlparse
import os
from bs4 import BeautifulSoup

def test_link_filtering():
    base_url = "http://dtri.sefaz.to.gov.br/legislacao/ntributaria/Leis/lei1287.htm"
    html_content = """
    <html>
        <body>
            <a href="xxla">Link Quebrado 1</a>
            <a href="javascript:void(0)">Link JS</a>
            <a href="mailto:teste@teste.com">Email</a>
            <a href="#">Anchor</a>
            <a href="lei1300.htm">Link Valido</a>
            <a href="  lei1400.htm  ">Link Valido com Espaço</a>
            <a href="../Leis/lei1500.htm">Link Relativo Valido</a>
        </body>
    </html>
    """
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    links = []
    
    IGNORED_PATTERNS = ['xxla', 'javascript:', 'mailto:', '#']
    IGNORED_EXTENSIONS = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
        '.zip', '.rar', '.7z', '.tar', '.gz', 
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv'
    }
    
    print(f"Base URL: {base_url}")
    print("-" * 50)

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        print(f"Processando href original: '{href}'")
        
        # Ignora links vazios ou com padrões ignorados
        if not href or any(p in href.lower() for p in IGNORED_PATTERNS):
            print(f"  -> IGNORADO (Padrão proibido no href)")
            continue
            
        # Resolve URLs relativas corretamente usando urljoin com a base corrigida
        # Limpa espaços em branco que podem quebrar a URL
        full_url = urljoin(base_url, href.strip())
        
        # Remove fragmentos
        full_url = full_url.split('#')[0]
        
        # Verifica novamente padrões ignorados na URL completa
        if any(p in full_url.lower() for p in IGNORED_PATTERNS):
            print(f"  -> IGNORADO (Padrão proibido na full_url: {full_url})")
            continue

        # Verifica extensão do arquivo
        try:
            parsed = urlparse(full_url)
            path = parsed.path.lower()
            ext = os.path.splitext(path)[1]
            if ext in IGNORED_EXTENSIONS:
                print(f"  -> IGNORADO (Extensão proibida: {ext})")
                continue
        except:
            pass

        print(f"  -> ACEITO: {full_url}")
        links.append(full_url)
    
    return links

if __name__ == "__main__":
    valid_links = test_link_filtering()
    print("-" * 50)
    print(f"Total links válidos: {len(valid_links)}")
    print(valid_links)
