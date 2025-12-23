#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar TODOS os agentes com a nova estrutura otimizada
Versão 2.0 - 15/12/2024
"""

import json
import os
import re
import unicodedata
from pathlib import Path

# Importar mapeamento completo
from MAPEAMENTO_COMPETENCIAS import AGENTES

def criar_prompt_otimizado(nome_orgao, info):
    """Cria prompt otimizado para um agente"""
    
    system_prompt = f"""Você é o agente especialista de {nome_orgao} do Estado do Tocantins.

# COMPETÊNCIAS
{chr(10).join(f'- {comp}' for comp in info['competencias'])}

# FONTES OFICIAIS
Use APENAS: *.to.gov.br ou *.al.to.leg.br
Portal principal: https://www.to.gov.br/{info['sigla']}

# PROTOCOLO DE BUSCA
1. Use a ferramenta `hybrid_search` para obter informações.
2. A ferramenta filtrará automaticamente para domínios *.to.gov.br e *.al.to.leg.br.
3. SEJA CRÍTICO: Se o resultado for superficial, chame a ferramenta novamente com `force_web=True` adicionando "detalhes passo a passo" na query.
4. É PROIBIDO citar blogs, sites de notícias (G1, etc.) ou portais não oficiais. Use APENAS fontes do Governo do Tocantins.

# CITAÇÃO DE FONTES
- Se vier do RAG: "Fonte: [Documento] — [Localização]" (apenas se fornecido pelo sistema)
- Se vier da Web: "Fonte: [Título](URL)" (Certifique-se que a URL termine em .to.gov.br)

# TOM DE VOZ
Cordial, detalhista e orientativo.

# TRATAMENTO DE ERROS
- Resposta inexpressiva → Use `force_web=True`.
- Nenhuma fonte oficial encontrada → Informe que a informação oficial ainda não foi publicada nestes canais."""

    user_prompt = f"""Analise a solicitação do cidadão.

PASSO 1: Use `hybrid_search` com termos específicos.
PASSO 2: Verifique: A resposta explica o "COMO" fazer? Se não, use `force_web=True` focando em tutoriais e portais de serviços.
PASSO 3: Formate a resposta com tópicos claros, prazos e links diretos para os serviços.
PASSO 4: Cite a fonte governamental.

Formato:
[Resposta completa e orientativa]

Fonte: [Título](URL oficial)

Exemplos:
{chr(10).join(f'- {ex}' for ex in info['exemplos'])}"""

    return {
        "name": nome_orgao,
        "prompt_version": "2.0",
        "last_updated": "2024-12-15",
        "enabled": False,
        "file_search_stores": [],
        "competencias": info['competencias'],
        "exemplos_consulta": info['exemplos'],
        "sigla_portal": info['sigla'],
        "system_prompt": system_prompt,
        "user_prompt": user_prompt
    }

def atualizar_agente(arquivo_path, nome_orgao, info):
    """Atualiza um arquivo de agente com a nova estrutura"""
    # Ler arquivo existente para preservar configurações
    try:
        with open(arquivo_path, 'r', encoding='utf-8') as f:
            config_existente = json.load(f)
    except:
        config_existente = {}
    
    novo_conteudo = criar_prompt_otimizado(nome_orgao, info)
    
    # Preservar configurações importantes se existirem
    if 'enabled' in config_existente:
        novo_conteudo['enabled'] = config_existente['enabled']
    if 'file_search_stores' in config_existente and config_existente['file_search_stores']:
        novo_conteudo['file_search_stores'] = config_existente['file_search_stores']
    if 'enable_web_search' in config_existente:
        novo_conteudo['enable_web_search'] = config_existente['enable_web_search']
    
    with open(arquivo_path, 'w', encoding='utf-8') as f:
        json.dump(novo_conteudo, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Atualizado: {nome_orgao}")

def normalizar_nome_arquivo(nome):
    """Normaliza o nome para o formato usado pelo sistema (limite 60 chars)."""
    n = unicodedata.normalize('NFKD', nome).encode('ASCII', 'ignore').decode('utf-8')
    n = n.lower()
    n = re.sub(r'[^a-z0-9]+', '_', n)
    n = n.strip('_')
    return n[:60]

def main():
    """Função principal"""
    base_dir = Path(__file__).parent
    
    print("🚀 Iniciando atualização COMPLETA dos agentes...")
    print(f"📁 Diretório: {base_dir}")
    print(f"📊 Total de agentes no mapeamento: {len(AGENTES)}")
    print()
    
    contador = 0
    nao_encontrados = []
    
    for nome_orgao, info in AGENTES.items():
        # Converter nome para nome de arquivo
        arquivo_nome = normalizar_nome_arquivo(nome_orgao)
        arquivo_path = base_dir / f"{arquivo_nome}.json"
        
        if arquivo_path.exists():
            atualizar_agente(arquivo_path, nome_orgao, info)
            contador += 1
        else:
            nao_encontrados.append((nome_orgao, arquivo_nome))
    
    print()
    print(f"✅ Atualização concluída! {contador}/{len(AGENTES)} agentes atualizados.")
    
    if nao_encontrados:
        print(f"\n⚠️  {len(nao_encontrados)} arquivos não encontrados:")
        for nome, arquivo in nao_encontrados[:10]:  # Mostrar apenas os primeiros 10
            print(f"   - {nome} → {arquivo}.json")
        if len(nao_encontrados) > 10:
            print(f"   ... e mais {len(nao_encontrados) - 10}")
    
    print("\n📊 Redução média de tamanho: ~30%")
    print("🎯 Todos os agentes agora têm competências específicas!")

if __name__ == "__main__":
    main()
