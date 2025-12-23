# Backup de Arquivos Scraped

Esta pasta contém cópias de segurança de todos os arquivos obtidos via web scraping antes de serem enviados para o RAG (Base de Conhecimento).

## Estrutura

```
scraped_backup/
├── secretaria-da-fazenda-xxx/
│   ├── ipva_2024_20241217_101530.md
│   ├── tributos_20241217_102045.md
│   └── ...
├── secretaria-da-educacao-xxx/
│   └── ...
└── ...
```

## Organização

- **Por Store**: Cada subpasta corresponde a uma base de conhecimento (store)
- **Com Timestamp**: Cada arquivo tem timestamp para evitar sobrescrever versões anteriores
- **Formato**: Markdown (.md) - mesmo formato enviado para o RAG

## Utilidade

1. **Auditoria**: Verificar o que foi adicionado à base
2. **Recuperação**: Restaurar conteúdo se necessário
3. **Análise**: Revisar qualidade do scraping
4. **Histórico**: Manter registro de quando cada conteúdo foi adicionado

## Limpeza

Você pode limpar arquivos antigos periodicamente para economizar espaço:
- Manter últimos 30 dias
- Ou manter apenas versões mais recentes de cada URL

## Exemplo de Nome de Arquivo

```
ipva_2024_20241217_101530.md
│         │        │      └─ Segundos
│         │        └─ Hora e minuto
│         └─ Data (YYYYMMDD)
└─ Nome original do arquivo
```
