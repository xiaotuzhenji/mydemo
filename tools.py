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
DATA_PATH = "data/scores_detail.csv"
df = pd.read_csv(DATA_PATH, dtype={"最低位次": str})  # 位次用字符串避免 NaN


@tool
def query_admission_score(query: str) -> str:
    """
    查询本地数据库中的大学专业级录取分数线。

    数据库：48所重点大学 × 10省 × 2024+2023年，含真实专业名称和位次。
    支持按大学、省份、年份、文理科、专业组合查询。
    例如："浙大计算机2024浙江"、"清华电子信息理科"。

    当用户问到分数线、录取分数、位次时优先使用本工具。

    参数 query: 用户的查询描述"""
    result = df.copy()

    # 按大学名称筛选（支持全名和简称）
    # 常用简称映射
    SHORT_NAMES = {
        "浙大": "浙江大学", "北大": "北京大学", "清华": "清华大学",
        "复旦": "复旦大学", "上交": "上海交通大学", "南大": "南京大学",
        "中科大": "中国科学技术大学", "哈工大": "哈尔滨工业大学",
        "西交": "西安交通大学", "人大": "中国人民大学", "同济": "同济大学",
        "武大": "武汉大学", "华科": "华中科技大学", "中大": "中山大学",
        "厦大": "厦门大学", "南开": "南开大学", "天大": "天津大学",
        "东南": "东南大学", "北航": "北京航空航天大学", "北理工": "北京理工大学",
        "华师大": "华东师范大学", "川大": "四川大学", "电子科大": "电子科技大学",
        "山大": "山东大学", "吉大": "吉林大学", "中南": "中南大学",
        "湖大": "湖南大学", "大工": "大连理工大学", "西工大": "西北工业大学",
    }
    universities = df["大学"].unique()
    # 先查简称映射
    query_univs = set()
    for short, full in SHORT_NAMES.items():
        if short in query and full in universities:
            query_univs.add(full)
    # 再查全名
    for u in universities:
        if u in query:
            query_univs.add(u)
    if query_univs:
        result = result[result["大学"].isin(query_univs)]

    # 按省份筛选
    for p in df["省份"].unique():
        if p in query:
            result = result[result["省份"] == p]
            break

    # 按文理科筛选
    if "理科" in query:
        result = result[result["文理科"] == "理科"]
    elif "文科" in query:
        result = result[result["文理科"] == "文科"]

    # 按专业筛选（模糊匹配），找不到则保留全部
    major_filters = {
        "计算机": "计算机|软件|人工智能|信息|数据|图灵",
        "软件": "软件|计算机",
        "电子": "电子|通信|集成电路|微电子",
        "医学": "医|临床|药学|护理",
        "金融": "金融|经济|财政|会计",
        "机械": "机械|车辆|制造",
        "土木": "土木|建筑|城规",
        "电气": "电气|自动化|能源",
        "法学": "法学|法律|知识产权",
        "数学": "数学|统计",
        "物理": "物理|应用物理",
        "化学": "化学|化工|材料",
        "生物": "生物|生医|生命",
    }
    for keyword, pattern in major_filters.items():
        if keyword in query:
            filtered = result[result["专业"].str.contains(pattern, case=False, na=False)]
            if len(filtered) > 0:  # 找到了才筛选，没找到保留全部
                result = filtered
            break

    # 按年份筛选
    years = sorted(df["年份"].unique(), reverse=True)
    for y in years:
        if str(y) in query:
            result = result[result["年份"] == y]
            break
    else:
        result = result[result["年份"] == years[0]]

    if result.empty:
        sample = ", ".join(sorted(universities)[:8])
        return (
            f"本地数据库未找到匹配数据。"
            f"数据库覆盖的大学包括：{sample}等48所。"
            f"请检查名称是否正确，或使用 web_search 工具联网搜索。"
        )

    # 格式化输出（最多20条，避免太长）
    lines = []
    for _, row in result.head(20).iterrows():
        rank_str = f"位次: {row['最低位次']}" if str(row['最低位次']).strip() else ""
        lines.append(
            f"{row['大学']} | {row['专业']} | {row['年份']}年 | {row['文理科']} | "
            f"最低分: {row['最低分']} | {rank_str} | {row['省份']}"
        )
    if len(result) > 20:
        lines.append(f"...（共{len(result)}条，仅显示前20条）")
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
# 工具 5：掌上高考实时查询（新）
# ============================================================
# 缓存学校列表（启动时加载一次）
_school_cache = None

def _get_school_list() -> dict:
    """获取学校名 → ID 映射"""
    global _school_cache
    if _school_cache is not None:
        return _school_cache

    try:
        import requests as _r
        url = "https://static-data.gaokao.cn/www/2.0/info/linkage.json"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.gaokao.cn/"}
        data = _r.get(url, headers=headers, timeout=30).json()
        schools = data.get("data", {}).get("school", [])
        _school_cache = {}
        for s in schools:
            name = s.get("name", "")
            sid = s.get("school_id", "")
            if name and sid:
                _school_cache[name] = str(sid)
        return _school_cache
    except Exception:
        return {}


# 省份编码
_PROVINCE_CODE = {
    "北京":11,"天津":12,"河北":13,"山西":14,"内蒙古":15,
    "辽宁":21,"吉林":22,"黑龙江":23,"上海":31,"江苏":32,
    "浙江":33,"安徽":34,"福建":35,"江西":36,"山东":37,
    "河南":41,"湖北":42,"湖南":43,"广东":44,"广西":45,
    "海南":46,"重庆":50,"四川":51,"贵州":52,"云南":53,
    "陕西":61,"甘肃":62,"青海":63,"宁夏":64,"新疆":65,
}


@tool
def query_live_score(query: str) -> str:
    """
    实时查询掌上高考官方 API 的专业级录取数据。

    支持近3000所大学，覆盖全国31省，2024+2023年最新数据。
    适用场景：
    - 本地数据库中没有的大学或省份
    - 需要最新、最全的专业级数据
    - 查特定专业的录取情况

    查询时请尽量提供大学名称、省份、年份。
    例如："四川大学四川2024"、"深圳大学广东计算机"

    参数 query: 查询描述，需包含大学名、省份、年份
    """
    try:
        import requests as _r
        import re as _re

        school_map = _get_school_list()
        if not school_map:
            return "学校列表加载失败，请稍后重试。"

        # 解析查询：提取大学名
        school_name = None
        # 先查简称
        _short = {"浙大":"浙江大学","北大":"北京大学","清华":"清华大学",
                  "复旦":"复旦大学","上交":"上海交通大学","南大":"南京大学",
                  "中科大":"中国科学技术大学","哈工大":"哈尔滨工业大学",
                  "西交":"西安交通大学","人大":"中国人民大学","同济":"同济大学",
                  "武大":"武汉大学","华科":"华中科技大学","中大":"中山大学",
                  "厦大":"厦门大学","南开":"南开大学","天大":"天津大学",
                  "东南":"东南大学","北航":"北京航空航天大学","北理工":"北京理工大学",
                  "华师大":"华东师范大学","川大":"四川大学","电子科大":"电子科技大学",
                  "山大":"山东大学","吉大":"吉林大学","中南":"中南大学",
                  "湖大":"湖南大学","大工":"大连理工大学","西工大":"西北工业大学",
                  "深大":"深圳大学","南科大":"南方科技大学","上财":"上海财经大学",
                  "央财":"中央财经大学","对外经贸":"对外经济贸易大学",
                  "北邮":"北京邮电大学","西电":"西安电子科技大学",
                  "北交":"北京交通大学","南航":"南京航空航天大学",
                  "南理":"南京理工大学","哈工程":"哈尔滨工程大学",
                  "华理":"华东理工大学","上大":"上海大学"}
        for short, full in _short.items():
            if short in query:
                school_name = full
                break
        if not school_name:
            for name in school_map:
                if name in query:
                    school_name = name
                    break

        if not school_name:
            return f"未能识别大学名称。请提供完整大学名（如\"四川大学\"）。"

        school_id = school_map.get(school_name)
        if not school_id:
            return f"未找到 {school_name} 的学校 ID。请检查名称是否正确。"

        # 解析省份和年份
        province_id = None
        for pname, pid in _PROVINCE_CODE.items():
            if pname in query:
                province_id = pid
                province_name = pname
                break
        if not province_id:
            province_id = 33  # 默认浙江
            province_name = "浙江"

        year = 2024
        for y in [2024, 2023, 2022, 2021]:
            if str(y) in query:
                year = y
                break

        # 调用 API
        url = f"https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{province_id}.json"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.gaokao.cn/"}
        resp = _r.get(url, headers=headers, timeout=15)
        data = resp.json()

        if data.get("code") != "0000":
            return f"API 返回错误: {data.get('message', '未知错误')}"

        rows = []
        for gk, gv in data.get("data", {}).items():
            for item in gv.get("item", []):
                info = item.get("info", "")
                m = _re.search(r"[（(](.+?)[，,)）]", info)
                major = m.group(1) if m else (info[:25] if info else "-")
                score = item.get("min", "")
                rank = item.get("min_section", "")
                subject = "理科" if item.get("type") == "1" else "文科"

                if score and str(score).replace(".", "").isdigit():
                    rows.append(f"{school_name} | {major} | {year}年 | {subject} | 最低分: {int(float(score))} | 位次: {rank} | {province_name}")

        if not rows:
            return f"{school_name} 在 {province_name} {year}年暂无录取数据。"

        return "\n".join(rows[:30])  # 最多返回30条

    except Exception as e:
        return f"实时查询失败: {e}。请尝试使用 query_admission_score 或 web_search。"


# ============================================================
# 工具列表
# ============================================================
TOOLS = [query_admission_score, web_search, query_knowledge_base, check_employment, query_live_score]
