from typing import List, Dict
import PyPDF2
import pandas as pd

class DocumentProcessor:

    @staticmethod
    def process_txt(file_path: str) -> List[Dict]:
        """Extrai texto de arquivo TXT"""
        chunks = []
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
            if text.strip():
                chunks.append({
                    "content": text,
                    "page": 1,
                    "type": "txt"
                })
        return chunks

    @staticmethod
    def process_pdf(file_path: str) -> List[Dict]:
        """Extrai texto de PDF"""
        chunks = []
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text.strip():
                    chunks.append({
                        "content": text,
                        "page": page_num + 1,
                        "type": "pdf"
                    })
        return chunks

    @staticmethod
    def process_excel(file_path: str) -> List[Dict]:
        """Extrai dados de Excel"""
        chunks = []
        xl_file = pd.ExcelFile(file_path)

        for sheet_name in xl_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)

            text = f"Planilha: {sheet_name}\n\n"
            text += f"Colunas: {', '.join(df.columns.astype(str))}\n\n"
            text += df.to_string()

            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                text += "\n\nResumo Estatístico:\n"
                text += df[numeric_cols].describe().to_string()

            chunks.append({
                "content": text,
                "sheet": sheet_name,
                "type": "excel",
                "rows": len(df),
                "columns": list(df.columns.astype(str))
            })

        return chunks

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Divide texto em chunks com overlap"""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)

        return chunks
