"""
Configurações para o serviço de scraping
"""

# Configurações do Scrapy
SCRAPY_SETTINGS = {
    'USER_AGENT': 'ADK-Scraper/1.0 (Educational Purpose)',
    'ROBOTSTXT_OBEY': True,
    'CONCURRENT_REQUESTS': 5,
    'DOWNLOAD_TIMEOUT': 10,
    'DOWNLOAD_DELAY': 1,  # 1 segundo entre requisições do mesmo domínio
    'COOKIES_ENABLED': False,
    'TELNETCONSOLE_ENABLED': False,
    'LOG_LEVEL': 'WARNING',
}

# Configurações do Playwright
PLAYWRIGHT_SETTINGS = {
    'HEADLESS': True,
    'TIMEOUT': 30000,  # 30 segundos
    'WAIT_UNTIL': 'networkidle',  # Aguarda até rede ficar ociosa
    'VIEWPORT': {'width': 1920, 'height': 1080},
}

# Configurações do conversor Markdown
MARKDOWN_SETTINGS = {
    'BODY_WIDTH': 0,  # Sem quebra de linha automática
    'IGNORE_LINKS': False,
    'IGNORE_IMAGES': False,
    'IGNORE_EMPHASIS': False,
    'SKIP_INTERNAL_LINKS': False,
    'INLINE_LINKS': True,
    'PROTECT_LINKS': True,
    'MARK_CODE': True,
}

# Configurações gerais
MAX_FILE_SIZE_MB = 5  # Tamanho máximo do arquivo Markdown gerado
MAX_CONCURRENT_TASKS = 5  # Máximo de URLs processadas simultaneamente
REQUEST_TIMEOUT = 5  # Timeout para detecção de tipo de site (segundos)

# Padrões para detecção de sites JavaScript
JS_FRAMEWORK_PATTERNS = [
    'react',
    'vue',
    'angular',
    'next.js',
    'nuxt',
    'gatsby',
    'svelte',
    '__NEXT_DATA__',
    'ng-version',
    'data-reactroot',
    'data-react-helmet',
]

# Tags HTML que indicam conteúdo principal
CONTENT_TAGS = [
    'article',
    'main',
    'section',
    '.content',
    '.post',
    '.article',
    '#content',
    '#main',
]
