"""
Storage Service - Abstrai acesso a imagens (local ou S3/R2)
"""
import os
import logging
from pathlib import Path
from typing import Optional, List, BinaryIO
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Interface abstrata para backends de storage"""

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        pass

    @abstractmethod
    def list_directory(self, path: str) -> List[str]:
        pass

    @abstractmethod
    def is_directory(self, path: str) -> bool:
        pass

    @abstractmethod
    def get_file(self, path: str) -> Optional[bytes]:
        pass

    @abstractmethod
    def get_file_url(self, path: str) -> Optional[str]:
        pass


class LocalStorageBackend(StorageBackend):
    """Backend para storage local"""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        logger.info(f"LocalStorage initialized with base_path: {self.base_path}")

    def _full_path(self, path: str) -> Path:
        return self.base_path / path

    def file_exists(self, path: str) -> bool:
        return self._full_path(path).exists()

    def list_directory(self, path: str = "") -> List[str]:
        full_path = self._full_path(path)
        if not full_path.exists() or not full_path.is_dir():
            return []
        return sorted([item.name for item in full_path.iterdir()])

    def is_directory(self, path: str) -> bool:
        return self._full_path(path).is_dir()

    def get_file(self, path: str) -> Optional[bytes]:
        full_path = self._full_path(path)
        if not full_path.exists() or not full_path.is_file():
            return None
        return full_path.read_bytes()

    def get_file_url(self, path: str) -> Optional[str]:
        # Para local, retorna None - o arquivo será servido diretamente
        return None

    def get_file_path(self, path: str) -> Optional[Path]:
        """Retorna o caminho completo do arquivo (apenas para local)"""
        full_path = self._full_path(path)
        if full_path.exists():
            return full_path
        return None


class S3StorageBackend(StorageBackend):
    """Backend para S3/Cloudflare R2"""

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str = None,
        access_key_id: str = None,
        secret_access_key: str = None,
        region: str = "auto"
    ):
        import boto3
        from botocore.config import Config

        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url

        # Configurar cliente S3
        config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )

        self.client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=config
        )

        logger.info(f"S3Storage initialized with bucket: {bucket_name}")

    def file_exists(self, path: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except:
            return False

    def list_directory(self, path: str = "") -> List[str]:
        """Lista objetos em um 'diretorio' no S3"""
        prefix = path.rstrip('/') + '/' if path else ''
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )

            items = []

            # Adicionar "pastas" (common prefixes)
            for prefix_obj in response.get('CommonPrefixes', []):
                folder_name = prefix_obj['Prefix'].rstrip('/').split('/')[-1]
                items.append(folder_name)

            # Adicionar arquivos
            for obj in response.get('Contents', []):
                key = obj['Key']
                if key != prefix:  # Ignorar o proprio diretorio
                    file_name = key.split('/')[-1]
                    if file_name:
                        items.append(file_name)

            return sorted(items)
        except Exception as e:
            logger.error(f"Error listing S3 directory {path}: {e}")
            return []

    def is_directory(self, path: str) -> bool:
        """Verifica se um path e um 'diretorio' no S3"""
        prefix = path.rstrip('/') + '/'
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=1
            )
            return response.get('KeyCount', 0) > 0
        except:
            return False

    def get_file(self, path: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=path)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Error getting file {path} from S3: {e}")
            return None

    def get_file_url(self, path: str, expires_in: int = 3600) -> Optional[str]:
        """Gera URL pre-assinada para acesso direto ao arquivo"""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': path},
                ExpiresIn=expires_in
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL for {path}: {e}")
            return None


class StorageService:
    """Servico principal de storage - singleton"""

    _instance = None
    _backend: StorageBackend = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Inicializa o backend baseado nas configuracoes"""
        from app.core.config import settings

        if self._backend is not None:
            return  # Ja inicializado

        if settings.STORAGE_TYPE == "s3":
            if not settings.S3_BUCKET_NAME:
                raise ValueError("S3_BUCKET_NAME is required when STORAGE_TYPE=s3")

            self._backend = S3StorageBackend(
                bucket_name=settings.S3_BUCKET_NAME,
                endpoint_url=settings.S3_ENDPOINT_URL or None,
                access_key_id=settings.S3_ACCESS_KEY_ID or None,
                secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
                region=settings.S3_REGION
            )
            logger.info("Storage: Using S3/R2 backend")
        else:
            # Local storage
            if settings.LOCAL_IMAGES_PATH:
                base_path = settings.LOCAL_IMAGES_PATH
            else:
                # Default: pasta portfolios_corrigidos na raiz do projeto
                base_path = Path(__file__).parent.parent.parent.parent / "portfolios_corrigidos"

            self._backend = LocalStorageBackend(str(base_path))
            logger.info(f"Storage: Using local backend at {base_path}")

    @property
    def backend(self) -> StorageBackend:
        if self._backend is None:
            self.initialize()
        return self._backend

    def file_exists(self, path: str) -> bool:
        return self.backend.file_exists(path)

    def list_directory(self, path: str = "") -> List[str]:
        return self.backend.list_directory(path)

    def is_directory(self, path: str) -> bool:
        return self.backend.is_directory(path)

    def get_file(self, path: str) -> Optional[bytes]:
        return self.backend.get_file(path)

    def get_file_url(self, path: str) -> Optional[str]:
        return self.backend.get_file_url(path)

    def get_local_path(self, path: str) -> Optional[Path]:
        """Retorna caminho local se backend for local"""
        if isinstance(self.backend, LocalStorageBackend):
            return self.backend.get_file_path(path)
        return None

    def is_local(self) -> bool:
        """Verifica se esta usando storage local"""
        return isinstance(self.backend, LocalStorageBackend)


# Instancia global
storage_service = StorageService()
