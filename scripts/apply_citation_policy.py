import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'dados', 'agentes')

def apply_policy_to_file(path: str) -> bool:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        sp = (data.get("system_prompt") or "").strip()
        up = (data.get("user_prompt") or "").strip()
        citation_header = "POLÍTICA DE CITAÇÕES"
        citation_block = (
            "POLÍTICA DE CITAÇÕES (CONDICIONAL):\n"
            "1. Base de Conhecimento (File Search): NÃO inclua URL na fonte. Cite como: "
            "\"Fonte: [Nome do documento da base] — [Capítulo/Seção/Artigo/Parágrafo/Inciso/Alínea/Página, quando disponível]\" "
            "e indique o trecho/localização onde a informação foi encontrada.\n"
            "2. Legislação: Informe número da lei, artigo, parágrafo (§), inciso e alínea; "
            "indique a localização no documento (Capítulo/Seção/Título/Página) quando possível.\n"
            "3. Pesquisa na Web: Inclua a URL oficial e aplique a regra 2 quando se tratar de legislação."
        )
        changed = False
        if citation_header not in sp:
            sp = (sp + "\n\n" + citation_block).strip()
            changed = True
        if "Regras de Citação:" not in up:
            up = (
                up + "\n\nRegras de Citação:\n"
                "- Se usou a Base: Fonte: [Nome do documento] — [Capítulo/Seção/Artigo/Parágrafo/Inciso/Alínea/Página, quando disponível].\n"
                "- Se for legislação: inclua número da lei e referências a artigo, parágrafo (§), inciso e alínea, com localização no documento.\n"
                "- Se usou Web: inclua a URL oficial."
            )
            changed = True
        if changed:
            data["system_prompt"] = sp
            data["user_prompt"] = up
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        return changed
    except Exception:
        return False

def main():
    if not os.path.exists(AGENTS_DIR):
        print("Agentes não encontrados")
        return
    total = 0
    updated = 0
    for fname in os.listdir(AGENTS_DIR):
        if not fname.endswith('.json'):
            continue
        total += 1
        fpath = os.path.join(AGENTS_DIR, fname)
        if apply_policy_to_file(fpath):
            updated += 1
    print(json.dumps({"total": total, "updated": updated}, ensure_ascii=False))

if __name__ == '__main__':
    main()
