import os
from pathlib import Path
from llama_index.core import Document
from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import FlatReader, DocxReader

from ..utils import hashstr, logger
from ..plugins import ocr


def chunk(text_or_path, params=None):
    """
    将文本或文件切分成固定大小的块

    Args:
        text_or_path: 文本或文件路径
        params: 参数
            chunk_size: 块大小
            chunk_overlap: 块重叠大小
            use_parser: 是否使用文件解析器
    Returns:
        nodes: 节点列表
    """
    params = params or {}
    chunk_size = int(params.get("chunk_size", 1000))
    chunk_overlap = int(params.get("chunk_overlap", 100))
    splitter = SentenceSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # 如果文件存在，则使用文件解析器
    if os.path.isfile(text_or_path) and os.path.exists(text_or_path):
        file_type = Path(text_or_path).suffix.lower()
        logger.info(f"Processing file: {text_or_path}, type: {file_type}")
        
        if file_type == ".pdf":
            # 对于PDF文件，始终读取正文，多级回退在 read_text 中完成
            logger.info(f"Reading PDF file: {text_or_path}")
            text_content = read_text(text_or_path)
            logger.info(f"PDF content length: {len(text_content)}")
            docs = [Document(id_=hashstr(text_or_path), text=text_content)]
        elif file_type in [".txt", ".json", ".md"]:
            docs = FlatReader().load_data(Path(text_or_path))
        elif file_type in [".docx"]:
            # 优先使用 docx2txt 直接提取正文，失败再回退 DocxReader
            try:
                import docx2txt  # type: ignore
                content = docx2txt.process(text_or_path) or ""
                docs = [Document(id_=hashstr(text_or_path), text=content)]
            except Exception:
                docs = DocxReader().load_data(Path(text_or_path))
        elif file_type in [".doc", ".csv", ".xlsx", ".xls"]:
            # 其他常见办公文件，读取为纯文本后再分块
            try:
                text_content = read_text(text_or_path)
                docs = [Document(id_=hashstr(text_or_path), text=text_content)]
            except Exception as e:
                logger.error(f"Failed to read office file {text_or_path}: {e}")
                docs = [Document(id_=hashstr(text_or_path), text=text_or_path)]
        else:
            logger.warning(f"Unsupported file type `{file_type}`, treating as text")
            docs = [Document(id_=hashstr(text_or_path), text=text_or_path)]

        if params and params.get("use_parser"):
            parser = SimpleFileNodeParser()
            nodes = parser.get_nodes_from_documents(docs)
        else:
            nodes = splitter.get_nodes_from_documents(docs)

    else:
        docs = [Document(id_=hashstr(text_or_path), text=text_or_path)]
        nodes = splitter.get_nodes_from_documents(docs)

    return nodes



def pdfreader(file_path):
    """读取PDF文件并返回text文本"""
    assert os.path.exists(file_path), "File not found"
    assert file_path.endswith(".pdf"), "File format not supported"

    from llama_index.readers.file import PDFReader
    doc = PDFReader().load_data(file=Path(file_path))

    # 简单的拼接起来之后返回纯文本
    text = "\n\n".join([d.get_content() for d in doc])
    return text

def plainreader(file_path):
    """读取普通文本文件并返回text文本"""
    assert os.path.exists(file_path), "File not found"

    with open(file_path, "r") as f:
        text = f.read()
    return text

def read_text(file, params=None):
    support_format = [".pdf", ".txt", ".md", ".doc", ".csv", ".xlsx", ".xls"]
    assert os.path.exists(file), "File not found"
    logger.info(f"Try to read file {file}")

    if not os.path.isfile(file):
        logger.error(f"Directory not supported now!")
        raise NotImplementedError("Directory not supported now!")

    if file.endswith(".pdf"):
        # 多级回退：PDFReader -> PyMuPDF(get_text) -> RapidOCR
        # 1) 结构化文本 PDFReader
        try:
            return pdfreader(file)
        except Exception as e:
            logger.warning(f"pdfreader failed: {e}")
        # 2) 直接用 PyMuPDF 提取文本
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file)
            parts = []
            for i in range(len(doc)):
                page = doc.load_page(i)
                parts.append(page.get_text() or "")
            text = "\n\n".join(parts)
            if text.strip():
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF get_text failed: {e}")
        # 3) RapidOCR 图像型 PDF
        return ocr.process_pdf(file)

    elif file.endswith(".txt") or file.endswith(".md"):
        return plainreader(file)

    elif file.endswith(".csv"):
        return csvreader(file)

    elif file.endswith(".xlsx") or file.endswith(".xls"):
        return excelreader(file)

    elif file.endswith(".doc"):
        return docreader(file)

    else:
        logger.error(f"File format not supported, only support {support_format}")
        raise Exception(f"File format not supported, only support {support_format}")


def csvreader(file_path):
    """读取CSV并拼接为纯文本"""
    import pandas as pd
    try:
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding="utf-8")
    except Exception:
        # 回退常见编码
        df = pd.read_csv(file_path, dtype=str, keep_default_na=False, encoding_errors="ignore")
    # 每行拼成一段
    lines = df.astype(str).apply(lambda r: " \t ".join(r.values.tolist()), axis=1).tolist()
    return "\n".join(lines)


def excelreader(file_path):
    """读取Excel（xlsx/xls）并拼接为纯文本（按工作表顺序）"""
    import pandas as pd
    # 读取所有工作表
    xls = pd.read_excel(file_path, sheet_name=None, dtype=str)
    texts = []
    for sheet_name, df in xls.items():
        texts.append(f"# Sheet: {sheet_name}")
        if df is None or df.empty:
            continue
        lines = df.fillna("").astype(str).apply(lambda r: " \t ".join(r.values.tolist()), axis=1).tolist()
        texts.append("\n".join(lines))
    return "\n\n".join(texts)


def docreader(file_path):
    """尝试读取旧版Word .doc 文本。
    优先使用 textract，其次尝试 antiword；若均不可用则抛错提示安装依赖。
    """
    try:
        import textract  # type: ignore
        content = textract.process(file_path)
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return str(content)
    except Exception:
        import shutil, subprocess
        if shutil.which("antiword"):
            res = subprocess.run(["antiword", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                return res.stdout.decode("utf-8", errors="ignore")
            else:
                raise Exception(f"antiword failed: {res.stderr.decode('utf-8', errors='ignore')}")
        raise Exception(".doc 解析需要依赖 textract 或 antiword，请在镜像中安装后重试")

