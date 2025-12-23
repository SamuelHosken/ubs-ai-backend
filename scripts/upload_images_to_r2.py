#!/usr/bin/env python3
"""
Script para fazer upload das imagens de portfolios para Cloudflare R2.

Uso:
    python scripts/upload_images_to_r2.py

Variaveis de ambiente necessarias:
    S3_BUCKET_NAME - Nome do bucket R2
    S3_ENDPOINT_URL - URL do endpoint R2 (https://<account_id>.r2.cloudflarestorage.com)
    S3_ACCESS_KEY_ID - Access Key ID do R2
    S3_SECRET_ACCESS_KEY - Secret Access Key do R2
"""

import os
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import mimetypes

# Adicionar o diretorio pai ao path para importar os modulos do app
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.config import Config
from dotenv import load_dotenv

# Carregar variaveis de ambiente
load_dotenv()

# Configuracoes
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
REGION = os.getenv("S3_REGION", "auto")

# Pasta local das imagens
LOCAL_IMAGES_PATH = Path(__file__).parent.parent.parent / "portfolios_corrigidos"

# Extensoes de imagem suportadas
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}


def validate_config():
    """Valida as configuracoes necessarias"""
    missing = []
    if not BUCKET_NAME:
        missing.append("S3_BUCKET_NAME")
    if not ENDPOINT_URL:
        missing.append("S3_ENDPOINT_URL")
    if not ACCESS_KEY_ID:
        missing.append("S3_ACCESS_KEY_ID")
    if not SECRET_ACCESS_KEY:
        missing.append("S3_SECRET_ACCESS_KEY")

    if missing:
        print("Erro: Variaveis de ambiente faltando:")
        for var in missing:
            print(f"  - {var}")
        print("\nPara Cloudflare R2:")
        print("  1. Va em Cloudflare Dashboard > R2 > Manage R2 API Tokens")
        print("  2. Crie um token com permissoes de Object Read & Write")
        print("  3. Configure as variaveis no .env")
        sys.exit(1)


def create_s3_client():
    """Cria cliente S3 configurado para R2"""
    config = Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )

    return boto3.client(
        's3',
        endpoint_url=ENDPOINT_URL,
        aws_access_key_id=ACCESS_KEY_ID,
        aws_secret_access_key=SECRET_ACCESS_KEY,
        region_name=REGION,
        config=config
    )


def get_content_type(filename: str) -> str:
    """Retorna o content-type baseado na extensao do arquivo"""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or 'application/octet-stream'


def upload_file(client, local_path: Path, s3_key: str) -> tuple[str, bool, str]:
    """
    Faz upload de um arquivo para o S3/R2.
    Retorna: (s3_key, success, message)
    """
    try:
        content_type = get_content_type(local_path.name)

        client.upload_file(
            str(local_path),
            BUCKET_NAME,
            s3_key,
            ExtraArgs={
                'ContentType': content_type,
                'CacheControl': 'public, max-age=31536000'  # 1 ano de cache
            }
        )
        return (s3_key, True, "OK")
    except Exception as e:
        return (s3_key, False, str(e))


def collect_files() -> list[tuple[Path, str]]:
    """Coleta todos os arquivos de imagem para upload"""
    files = []

    if not LOCAL_IMAGES_PATH.exists():
        print(f"Erro: Pasta de imagens nao encontrada: {LOCAL_IMAGES_PATH}")
        sys.exit(1)

    for file_path in LOCAL_IMAGES_PATH.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTENSIONS:
            # Criar key S3 relativa a pasta base
            s3_key = str(file_path.relative_to(LOCAL_IMAGES_PATH))
            files.append((file_path, s3_key))

    return files


def main():
    print("=" * 60)
    print("Upload de Imagens para Cloudflare R2")
    print("=" * 60)

    # Validar configuracoes
    validate_config()

    print(f"\nBucket: {BUCKET_NAME}")
    print(f"Endpoint: {ENDPOINT_URL}")
    print(f"Pasta local: {LOCAL_IMAGES_PATH}")

    # Criar cliente S3
    print("\nConectando ao R2...")
    client = create_s3_client()

    # Testar conexao
    try:
        client.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket '{BUCKET_NAME}' acessivel!")
    except Exception as e:
        print(f"Erro ao acessar bucket: {e}")
        print("\nVerifique se:")
        print("  1. O bucket existe")
        print("  2. As credenciais estao corretas")
        print("  3. O token tem permissoes de leitura/escrita")
        sys.exit(1)

    # Coletar arquivos
    print("\nColetando arquivos...")
    files = collect_files()
    total_files = len(files)
    print(f"Encontrados {total_files} arquivos de imagem")

    if total_files == 0:
        print("Nenhum arquivo para upload!")
        return

    # Confirmar upload
    response = input(f"\nDeseja fazer upload de {total_files} arquivos? (s/n): ")
    if response.lower() != 's':
        print("Upload cancelado.")
        return

    # Fazer upload em paralelo
    print("\nIniciando upload...")
    success_count = 0
    error_count = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(upload_file, client, local_path, s3_key): s3_key
            for local_path, s3_key in files
        }

        for i, future in enumerate(as_completed(futures), 1):
            s3_key, success, message = future.result()

            if success:
                success_count += 1
                # Mostrar progresso a cada 50 arquivos
                if success_count % 50 == 0 or i == total_files:
                    print(f"  Progresso: {i}/{total_files} ({100*i//total_files}%)")
            else:
                error_count += 1
                print(f"  Erro: {s3_key} - {message}")

    print("\n" + "=" * 60)
    print("Upload concluido!")
    print(f"  Sucesso: {success_count}")
    print(f"  Erros: {error_count}")
    print("=" * 60)

    if success_count > 0:
        print("\nProximo passo:")
        print("  Configure as variaveis de ambiente no Railway:")
        print(f"    STORAGE_TYPE=s3")
        print(f"    S3_BUCKET_NAME={BUCKET_NAME}")
        print(f"    S3_ENDPOINT_URL={ENDPOINT_URL}")
        print(f"    S3_ACCESS_KEY_ID=<seu_access_key>")
        print(f"    S3_SECRET_ACCESS_KEY=<seu_secret_key>")
        print(f"    S3_REGION=auto")


if __name__ == "__main__":
    main()
