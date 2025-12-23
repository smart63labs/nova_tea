import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def clean_old_backups(days_to_keep=30, dry_run=True):
    """
    Remove backups mais antigos que X dias
    
    Args:
        days_to_keep: Número de dias para manter (padrão: 30)
        dry_run: Se True, apenas mostra o que seria deletado sem deletar
    """
    backup_dir = Path("C:/Users/88417646191/Documents/ADK/dados/scraped_backup")
    
    if not backup_dir.exists():
        print("❌ Pasta de backup não existe")
        return
    
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    deleted_count = 0
    kept_count = 0
    total_size_deleted = 0
    
    print(f"🔍 Procurando backups mais antigos que {days_to_keep} dias...")
    print(f"   Data de corte: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Percorre todas as stores
    for store_dir in backup_dir.iterdir():
        if not store_dir.is_dir():
            continue
        
        print(f"\n📁 Store: {store_dir.name}")
        
        # Percorre arquivos da store
        for file_path in store_dir.glob("*.md"):
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            file_size = file_path.stat().st_size
            
            if file_mtime < cutoff_date:
                if dry_run:
                    print(f"   🗑️  [DRY RUN] Deletaria: {file_path.name} ({file_size} bytes)")
                else:
                    file_path.unlink()
                    print(f"   ✅ Deletado: {file_path.name} ({file_size} bytes)")
                
                deleted_count += 1
                total_size_deleted += file_size
            else:
                kept_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESUMO:")
    print(f"   🗑️  Arquivos {'que seriam ' if dry_run else ''}deletados: {deleted_count}")
    print(f"   ✅ Arquivos mantidos: {kept_count}")
    print(f"   💾 Espaço {'que seria ' if dry_run else ''}liberado: {total_size_deleted / 1024:.2f} KB")
    
    if dry_run:
        print(f"\n⚠️  MODO DRY RUN - Nenhum arquivo foi deletado")
        print(f"   Execute com dry_run=False para deletar de verdade")

def list_backups_by_store():
    """Lista todos os backups organizados por store"""
    backup_dir = Path("C:/Users/88417646191/Documents/ADK/dados/scraped_backup")
    
    if not backup_dir.exists():
        print("❌ Pasta de backup não existe")
        return
    
    print("📚 BACKUPS POR STORE")
    print("=" * 60)
    
    total_files = 0
    total_size = 0
    
    for store_dir in sorted(backup_dir.iterdir()):
        if not store_dir.is_dir():
            continue
        
        files = list(store_dir.glob("*.md"))
        if not files:
            continue
        
        store_size = sum(f.stat().st_size for f in files)
        total_files += len(files)
        total_size += store_size
        
        print(f"\n📁 {store_dir.name}")
        print(f"   Arquivos: {len(files)}")
        print(f"   Tamanho: {store_size / 1024:.2f} KB")
        
        # Mostra os 3 mais recentes
        recent_files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[:3]
        print(f"   Mais recentes:")
        for f in recent_files:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"      - {f.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
    
    print("\n" + "=" * 60)
    print(f"📊 TOTAL:")
    print(f"   Arquivos: {total_files}")
    print(f"   Tamanho: {total_size / 1024:.2f} KB ({total_size / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            list_backups_by_store()
        
        elif command == "clean":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
            dry_run = sys.argv[3] != "confirm" if len(sys.argv) > 3 else True
            clean_old_backups(days_to_keep=days, dry_run=dry_run)
        
        else:
            print("Comandos disponíveis:")
            print("  python manage_scraped_backups.py list")
            print("  python manage_scraped_backups.py clean [dias] [confirm]")
            print("\nExemplos:")
            print("  python manage_scraped_backups.py list")
            print("  python manage_scraped_backups.py clean 30        # Dry run")
            print("  python manage_scraped_backups.py clean 30 confirm  # Deleta de verdade")
    else:
        # Modo interativo
        print("🔧 GERENCIADOR DE BACKUPS DE SCRAPING")
        print("=" * 60)
        print("\n1. Listar backups")
        print("2. Limpar backups antigos (dry run)")
        print("3. Limpar backups antigos (CONFIRMAR)")
        print("0. Sair")
        
        choice = input("\nEscolha uma opção: ")
        
        if choice == "1":
            list_backups_by_store()
        elif choice == "2":
            days = input("Quantos dias manter? (padrão: 30): ")
            days = int(days) if days else 30
            clean_old_backups(days_to_keep=days, dry_run=True)
        elif choice == "3":
            days = input("Quantos dias manter? (padrão: 30): ")
            days = int(days) if days else 30
            confirm = input(f"⚠️  CONFIRMA deletar backups com mais de {days} dias? (sim/não): ")
            if confirm.lower() == "sim":
                clean_old_backups(days_to_keep=days, dry_run=False)
            else:
                print("❌ Operação cancelada")
