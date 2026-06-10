"""
RAG 知识库 —— ChromaDB + 云端 Embedding

用法：
  python rag.py              → 构建知识库
  python rag.py --query "..." → 测试查询
"""
import os
import sys
import glob
import shutil
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()

# ============================================================
# 配置
# ============================================================
DOCS_DIR = "data/documents"
CHROMA_DIR = "chroma_db"

TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
    separators=["\n\n", "\n", "。", "；", "，", " ", ""],
)


# ============================================================
# 0. 创建 Embedding 客户端
# ============================================================
def get_embedding():
    """
    云端 embedding 客户端。

    支持两种方式（在 .env 中配置）：
      EMBEDDING_PROVIDER=siliconflow   → 硅基流动（推荐，免费额度）
      EMBEDDING_PROVIDER=openai        → OpenAI（付费）
    """
    provider = os.getenv("EMBEDDING_PROVIDER", "siliconflow")

    if provider == "siliconflow":
        # 硅基流动：免费，中文效果好
        # 注册地址: https://siliconflow.cn
        # 模型可选: BAAI/bge-large-zh-v1.5, netease-youdao/bce-embedding-base_v1
        return OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-zh-v1.5"),
            api_key=os.getenv("EMBEDDING_API_KEY"),
            base_url="https://api.siliconflow.cn/v1",
            check_embedding_ctx_length=False,  # 硅基流动不兼容 tiktoken 预处理
        )
    else:
        # OpenAI
        return OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            api_key=os.getenv("EMBEDDING_API_KEY"),
        )


# ============================================================
# 1. 加载文档
# ============================================================
def load_documents(docs_dir: str = DOCS_DIR) -> list[Document]:
    documents = []
    files = glob.glob(f"{docs_dir}/*.txt")

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        if len(text.strip()) < 50:
            continue

        title = os.path.basename(filepath)
        for line in text.split("\n")[:3]:
            if line.startswith("# "):
                title = line[2:].strip()
                break

        documents.append(Document(
            page_content=text,
            metadata={"source": title, "file": filepath},
        ))

    return documents


# ============================================================
# 2. 构建向量库
# ============================================================
def build_vectorstore(force_rebuild: bool = False) -> Chroma:
    embedding = get_embedding()

    if force_rebuild and os.path.exists(CHROMA_DIR):
        shutil.rmtree(CHROMA_DIR)
        print("已删除旧知识库")

    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        print(f"加载已有知识库: {CHROMA_DIR}")
        return Chroma(embedding_function=embedding, persist_directory=CHROMA_DIR)

    print("构建新知识库...")
    documents = load_documents()
    print(f"  加载 {len(documents)} 篇文档")

    chunks = TEXT_SPLITTER.split_documents(documents)
    print(f"  切分 {len(chunks)} 个文本块")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding,
        persist_directory=CHROMA_DIR,
    )
    print(f"  已保存到 {CHROMA_DIR}")
    return vectorstore


# ============================================================
# 3. 查询
# ============================================================
def query(vectorstore: Chroma, question: str, k: int = 4) -> list[Document]:
    return vectorstore.similarity_search(question, k=k)


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--query":
        question = " ".join(sys.argv[2:]) or "平行志愿是什么意思"
        print(f"查询: {question}\n")
        vs = build_vectorstore()
        docs = query(vs, question)
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "?")
            print(f"--- 结果 {i} (来源: {source}) ---")
            print(doc.page_content[:300])
            print()
    else:
        print("=" * 50)
        print("  RAG 知识库构建")
        print("=" * 50)
        build_vectorstore(force_rebuild=True)
        print("\n构建完成！")
