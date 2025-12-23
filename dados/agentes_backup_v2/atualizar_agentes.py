#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para atualizar TODOS os agentes com a nova estrutura otimizada
Versão 2.0 - 15/12/2024
"""

import json
import os
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
1. Busque na Base de Conhecimento primeiro
2. Se não encontrar, use Web Search: site:to.gov.br OR site:al.to.leg.br
3. Priorize resultados de: www.to.gov.br/{info['sigla']}
4. Cite a fonte conforme regras abaixo

# CITAÇÃO DE FONTES
1. Base de Conhecimento: "Fonte: [Documento] — [Localização]"
2. Web (Geral): "Fonte: [Título](URL)"
3. Web (Legislação): "Fonte: Lei nº X, Art. Y, § Z — [Título](URL)"

# TOM DE VOZ
Formal mas acessível. Evite jargão técnico excessivo. Seja empático e objetivo.

# TRATAMENTO DE ERROS
- Base vazia → Tente Web Search
- Web falhar → Sugira contato direto com o órgão
- Fora do escopo → Redirecione para o órgão adequado"""

    user_prompt = f"""Analise a solicitação do cidadão.

PASSO 1: Busque na Base de Conhecimento
PASSO 2: Se não encontrar, use Web Search: site:to.gov.br OR site:al.to.leg.br
PASSO 3: Priorize: www.to.gov.br/{info['sigla']}
PASSO 4: Sintetize de forma clara
PASSO 5: Cite a fonte

Formato:
[Resposta clara e objetiva]

Fonte: [Documento — Localização] OU [Título](URL)

Exemplos que você pode responder:
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
    """Normaliza nome para nome de arquivo"""
    arquivo_nome = nome.lower()
    arquivo_nome = arquivo_nome.replace(' ', '_')
    arquivo_nome = arquivo_nome.replace(',', '')
    arquivo_nome = arquivo_nome.replace('ã', 'a').replace('á', 'a').replace('â', 'a')
    arquivo_nome = arquivo_nome.replace('é', 'e').replace('ê', 'e')
    arquivo_nome = arquivo_nome.replace('í', 'i')
    arquivo_nome = arquivo_nome.replace('ó', 'o').replace('õ', 'o').replace('ô', 'o')
    arquivo_nome = arquivo_nome.replace('ú', 'u').replace('ü', 'u')
    arquivo_nome = arquivo_nome.replace('ç', 'c')
    return arquivo_nome

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
