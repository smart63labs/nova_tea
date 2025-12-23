import json
import os
from pathlib import Path

# Diretório dos agentes
AGENTES_DIR = Path("C:/Users/88417646191/Documents/ADK/dados/agentes")

# Novo user_prompt melhorado
NEW_USER_PROMPT = """⚠️ REGRA CRÍTICA: TODA resposta DEVE incluir fonte. Respostas sem fonte são INVÁLIDAS.

FORMATO OBRIGATÓRIO DA RESPOSTA:
[Sua resposta clara e objetiva aqui]

**Fonte:** [Nome do Documento] — [Localização] OU [Título](URL)

PASSOS:
1. Busque na Base de Conhecimento primeiro
2. Se não encontrar, use Web Search: site:to.gov.br OR site:al.to.leg.br
3. Priorize resultados do portal específico deste órgão
4. Sintetize a resposta de forma clara e objetiva
5. SEMPRE cite a fonte usando o formato acima

EXEMPLOS DE CITAÇÃO CORRETA:
✅ Base: "**Fonte:** Decreto 5.123/2024 — Art. 3º, § 2º" (Sem URL)
✅ Web: "**Fonte:** [IPVA 2024](https://www.to.gov.br/sefaz/ipva)"
✅ Legislação: "**Fonte:** Lei nº 1.287/2001, Art. 15 — [Código Tributário](URL)"

⚠️ PROIBIÇÃO: JAMAIS gere links clicáveis para a Base de Conhecimento.

❌ ERRADO: Responder sem incluir a seção "**Fonte:**" """

def update_agent_prompts():
    """Atualiza os prompts de todos os agentes"""
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Lista todos os arquivos JSON no diretório
    agent_files = list(AGENTES_DIR.glob("*.json"))
    
    print(f"Encontrados {len(agent_files)} arquivos JSON")
    print("=" * 60)
    
    for agent_file in agent_files:
        # Pula o orquestrador e o template
        if agent_file.name in ["orquestrador.json", "_template.json"]:
            print(f"⏭️  Pulando: {agent_file.name}")
            skipped_count += 1
            continue
        
        try:
            # Lê o arquivo
            with open(agent_file, 'r', encoding='utf-8') as f:
                agent_data = json.load(f)
            
            # Verifica se tem user_prompt
            if 'user_prompt' not in agent_data:
                print(f"⚠️  {agent_file.name}: Não tem user_prompt, pulando...")
                skipped_count += 1
                continue
            
            # Atualiza o user_prompt
            old_prompt = agent_data['user_prompt']
            agent_data['user_prompt'] = NEW_USER_PROMPT
            
            # Atualiza o system_prompt para incluir citação obrigatória
            if 'system_prompt' in agent_data:
                system_prompt = agent_data['system_prompt']
                
                # Se já tem seção de citação, substitui
                if '# CITAÇÃO DE FONTES' in system_prompt:
                    # Encontra e substitui a seção
                    lines = system_prompt.split('\\n')
                    new_lines = []
                    skip_until_next_section = False
                    
                    for line in lines:
                        if line.startswith('# CITAÇÃO DE FONTES'):
                            # Adiciona nova seção
                            new_lines.append('# CITAÇÃO DE FONTES (OBRIGATÓRIO)')
                            new_lines.append('⚠️ TODA resposta DEVE incluir fonte. Respostas sem fonte são INVÁLIDAS.')
                            new_lines.append('')
                            new_lines.append('Formatos:')
                            new_lines.append('1. Base de Conhecimento: "**Fonte:** [Nome do Documento] — [Capítulo/Seção/Artigo/Parágrafo/Página]"')
                            new_lines.append('   - JAMAIS gere links clicáveis (URL) para a Base de Conhecimento.')
                            new_lines.append('2. Web (Geral): "**Fonte:** [Título da Página](URL)"')
                            new_lines.append('3. Web (Legislação): "**Fonte:** Lei nº X, Art. Y, § Z — [Título](URL)"')
                            skip_until_next_section = True
                            continue
                        
                        if skip_until_next_section:
                            if line.startswith('# '):
                                skip_until_next_section = False
                                new_lines.append(line)
                            continue
                        
                        new_lines.append(line)
                    
                    agent_data['system_prompt'] = '\\n'.join(new_lines)
            
            # Salva o arquivo atualizado
            with open(agent_file, 'w', encoding='utf-8') as f:
                json.dump(agent_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {agent_file.name}: Atualizado com sucesso")
            updated_count += 1
            
        except Exception as e:
            print(f"❌ {agent_file.name}: Erro - {str(e)}")
            error_count += 1
    
    print("=" * 60)
    print(f"\n📊 RESUMO:")
    print(f"   ✅ Atualizados: {updated_count}")
    print(f"   ⏭️  Pulados: {skipped_count}")
    print(f"   ❌ Erros: {error_count}")
    print(f"   📁 Total: {len(agent_files)}")
    
    return updated_count, skipped_count, error_count

if __name__ == "__main__":
    print("🚀 Iniciando atualização de prompts dos agentes...")
    print("=" * 60)
    update_agent_prompts()
    print("\n✨ Atualização concluída!")
