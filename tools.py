"""
Agent 工具集 —— 给 LLM 提供"手"
├── query_admission_score: 查本地数据库（精确、可靠）
└── web_search: 联网搜索（实时、覆盖面广）
"""
import pandas as pd
from langchain_core.tools import tool
from ddgs import DDGS

# ============================================================
# 工具 1：本地数据库查询（保留）
# ============================================================
DATA_PATH = "data/scores.csv"
df = pd.read_csv(DATA_PATH)


@tool
def query_admission_score(query: str) -> str:
    """
    查询本地数据库中的大学录取分数线（181所大学，13省，2021-2023年数据）。

    支持按大学名称、省份、年份、文理科组合查询。
    例如："浙江大学2023年浙江理科分数线"、"上海复旦大学文科最低分"。

    当用户问到分数线、录取分数、位次时优先使用本工具。

    参数 query: 用户的查询描述"""
    result = df.copy()

    # 按大学名称筛选（181所大学全量匹配）
    universities = df["大学"].unique()
    matched_univ = [u for u in universities if u in query]
    if matched_univ:
        result = result[result["大学"].isin(matched_univ)]

    # 按省份筛选
    provinces = df["省份"].unique()
    for p in provinces:
        if p in query:
            result = result[result["省份"] == p]
            break

    # 按文理科筛选
    if "理科" in query:
        result = result[result["批次"].str.contains("理科", case=False)]
    elif "文科" in query:
        result = result[result["批次"].str.contains("文科", case=False)]

    # 按年份筛选
    years = sorted(df["年份"].unique(), reverse=True)
    for y in years:
        if str(y) in query:
            result = result[result["年份"] == y]
            break
    else:
        result = result[result["年份"] == years[0]]

    if result.empty:
        # 给出前8所大学名作为参考
        sample = ", ".join(sorted(universities)[:8])
        return (
            f"本地数据库未找到匹配数据。"
            f"数据库覆盖 181 所大学，包括：{sample}等。"
            f"请检查大学名称是否正确，或使用 web_search 工具联网搜索。"
        )

    lines = []
    for _, row in result.iterrows():
        lines.append(
            f"{row['大学']} | {row['年份']}年 | {row['批次']} | "
            f"最低分: {row['最低分']} | 位次: {row['最低位次']} | {row['省份']}"
        )
    return "\n".join(lines)


# ============================================================
# 工具 2：联网搜索（新增）
# ============================================================
@tool
def web_search(query: str) -> str:
    """
    联网搜索高考志愿填报相关信息。

    用于查询以下类型的问题：
    - 本地数据库中没有的大学分数线
    - 最新的招生政策、录取规则
    - 专业介绍、就业前景
    - 院校排名、学科评估
    - 高考改革最新动态
    - 任何需要最新、实时信息的问题

    参数 query: 搜索关键词，建议包含年份和省份以获得准确结果
    """
    try:
        with DDGS() as ddgs:
            # 搜索 5 条结果
            results = list(ddgs.text(f"高考 {query}", max_results=5))

        if not results:
            return "未找到相关搜索结果。"

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"[{i}] {title}\n{body}\n来源: {href}\n")

        return "\n".join(lines)

    except Exception as e:
        return f"搜索失败: {e}。请稍后重试或使用本地数据库查询。"


# ============================================================
# 工具 3：RAG 知识库查询（新增）
# ============================================================
# 延迟加载，避免启动时就加载向量库
_vectorstore = None


def _get_vectorstore():
    global _vectorstore
    if _vectorstore is None:
        from rag import build_vectorstore
        _vectorstore = build_vectorstore()
    return _vectorstore


@tool
def query_knowledge_base(question: str) -> str:
    """
    查询高考志愿填报知识库。

    知识库包含以下内容：
    - 平行志愿、投档线、录取批次等核心概念解释
    - 计算机、软件工程、临床医学、金融学等专业介绍和就业前景
    - 冲稳保策略、志愿填报技巧和常见误区
    - 新高考选科要求、双一流大学排名、学科评估
    - 服从调剂、退档、滑档等术语解释

    当用户询问概念解释、政策规则、填报策略、专业介绍时优先使用。
    注意：本工具不查分数线，分数线请用 query_admission_score。

    参数 question: 用户的问题或查询关键词
    """
    try:
        vs = _get_vectorstore()
        docs = vs.similarity_search(question, k=4)

        if not docs:
            return "知识库中未找到相关信息。"

        lines = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "未知来源")
            content = doc.page_content[:400]  # 截断过长内容
            lines.append(f"[{i}] 来源: {source}\n{content}\n")

        return "\n".join(lines)

    except Exception as e:
        return f"知识库查询失败: {e}"


# ============================================================
# 工具 4：用人单位查询（"500强测试"）
# ============================================================
@tool
def check_employment(university: str, major: str = "") -> str:
    """
    查询某所大学毕业生的真实就业去向和雇主情况。

    用于回答以下问题：
    - 某大学毕业生都去了哪些公司？
    - 某专业好不好找工作？招聘企业有哪些？
    - 500强企业会去这所学校招聘吗？
    - 某个行业的真实用人情况

    参数 university: 大学名称
    参数 major: 专业名称（可选，不填则查全校情况）
    """
    try:
        query_parts = [university]
        if major:
            query_parts.append(major)
        query_parts.append("毕业生 就业去向 招聘企业 就业质量报告")

        search_query = " ".join(query_parts)

        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=5))

        if not results:
            return f"未找到 {university} 的就业数据。请尝试用更简短的名称搜索。"

        lines = [f"【{university}{' ' + major if major else ''} 就业去向】\n"]
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r.get('title', '')}")
            lines.append(f"    {r.get('body', '')[:200]}")
            lines.append(f"    {r.get('href', '')}\n")

        return "\n".join(lines)

    except Exception as e:
        return f"就业数据查询失败: {e}。请稍后重试。"


# ============================================================
# 工具列表
# ============================================================
TOOLS = [query_admission_score, web_search, query_knowledge_base, check_employment]
