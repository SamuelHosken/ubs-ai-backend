#!/usr/bin/env python3
"""
Script para configurar o ambiente de desenvolvimento do UBS Portfolio AI
Gera SECRET_KEY segura e valida configurações
"""

import secrets
import os
from pathlib import Path

def generate_secret_key():
    """Gera uma SECRET_KEY segura"""
    return secrets.token_urlsafe(32)

def check_env_file():
    """Verifica se .env existe"""
    env_path = Path(__file__).parent.parent / ".env"
    return env_path.exists()

def create_env_from_example():
    """Cria .env a partir do .env.example"""
    backend_dir = Path(__file__).parent.parent
    example_path = backend_dir / ".env.example"
    env_path = backend_dir / ".env"
    
    if not example_path.exists():
        print("❌ Erro: .env.example não encontrado!")
        return False
    
    if env_path.exists():
        response = input("⚠️  .env já existe. Sobrescrever? (y/N): ")
        if response.lower() != 'y':
            print("Operação cancelada.")
            return False
    
    # Ler template
    with open(example_path, 'r') as f:
        content = f.read()
    
    # Gerar SECRET_KEY
    secret_key = generate_secret_key()
    
    # Substituir placeholder
    content = content.replace(
        "SECRET_KEY=CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_MIN_32_CHARS",
        f"SECRET_KEY={secret_key}"
    )
    
    # Escrever .env
    with open(env_path, 'w') as f:
        f.write(content)
    
    print("✅ Arquivo .env criado com sucesso!")
    print(f"✅ SECRET_KEY gerada: {secret_key[:10]}... (32 chars)")
    print("\n📝 PRÓXIMOS PASSOS:")
    print("1. Edite o arquivo .env e adicione sua OPENAI_API_KEY")
    print("2. (Opcional) Adicione COHERE_API_KEY para reranking")
    print("3. Ajuste outras configurações conforme necessário")
    
    return True

def validate_env():
    """Valida as configurações do .env"""
    try:
        # Carregar .env
        from dotenv import load_dotenv
        load_dotenv()
        
        issues = []
        
        # Verificar SECRET_KEY
        secret_key = os.getenv("SECRET_KEY", "")
        if not secret_key or secret_key == "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING_MIN_32_CHARS":
            issues.append("❌ SECRET_KEY não configurada")
        elif len(secret_key) < 32:
            issues.append("❌ SECRET_KEY deve ter pelo menos 32 caracteres")
        else:
            print("✅ SECRET_KEY configurada corretamente")
        
        # Verificar OPENAI_API_KEY
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if not openai_key or openai_key.startswith("sk-your"):
            issues.append("⚠️  OPENAI_API_KEY não configurada (funcionalidade de IA não funcionará)")
        elif not openai_key.startswith("sk-"):
            issues.append("⚠️  OPENAI_API_KEY parece inválida (deve começar com 'sk-')")
        else:
            print("✅ OPENAI_API_KEY configurada")
        
        # Verificar COHERE_API_KEY (opcional)
        cohere_key = os.getenv("COHERE_API_KEY", "")
        if cohere_key:
            print("✅ COHERE_API_KEY configurada (reranking habilitado)")
        else:
            print("ℹ️  COHERE_API_KEY não configurada (reranking desabilitado)")
        
        # Verificar DATABASE_URL
        db_url = os.getenv("DATABASE_URL", "")
        if db_url:
            print(f"✅ DATABASE_URL: {db_url}")
        
        if issues:
            print("\n⚠️  PROBLEMAS ENCONTRADOS:")
            for issue in issues:
                print(f"  {issue}")
            return False
        
        print("\n🎉 Todas as configurações essenciais estão corretas!")
        return True
        
    except ImportError:
        print("⚠️  python-dotenv não instalado. Instale com: pip install python-dotenv")
        return False

def main():
    print("=" * 60)
    print("🔧 Setup do UBS Portfolio AI - Backend")
    print("=" * 60)
    print()
    
    # Verificar se .env existe
    if not check_env_file():
        print("📄 Arquivo .env não encontrado.")
        response = input("Deseja criar a partir do .env.example? (Y/n): ")
        if response.lower() != 'n':
            if create_env_from_example():
                print("\n" + "=" * 60)
                print("🔍 Validando configurações...")
                print("=" * 60)
                validate_env()
        else:
            print("\n💡 Dica: Copie .env.example para .env manualmente")
            print("   cp .env.example .env")
    else:
        print("✅ Arquivo .env encontrado!")
        print("\n" + "=" * 60)
        print("🔍 Validando configurações...")
        print("=" * 60)
        validate_env()
    
    print("\n" + "=" * 60)
    print("💡 COMANDOS ÚTEIS:")
    print("=" * 60)
    print("# Gerar nova SECRET_KEY:")
    print("  python -c 'import secrets; print(secrets.token_urlsafe(32))'")
    print()
    print("# Ingerir documentos:")
    print("  python scripts/ingest_documents.py")
    print()
    print("# Rodar servidor:")
    print("  uvicorn app.main:app --reload")
    print("=" * 60)

if __name__ == "__main__":
    main()
