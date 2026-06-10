"""
知识采集器 —— 为 RAG 准备文档

三种采集方式（按优先级）：
  1. ddgs 搜索采集 → 搜指定主题，保存搜索结果摘要
  2. 网页爬取     → 爬取可访问的 URL（自动跳过反爬的）
  3. 手动放入     → 直接把 txt/pdf 丢到 data/documents/

用法：
  python crawler.py              → 搜索采集（默认）
  python crawler.py --url URL    → 爬取指定网页
"""
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from ddgs import DDGS

# ============================================================
# 配置
# ============================================================
OUTPUT_DIR = "data/documents"
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 2.0  # ddgs 搜索间隔


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


# ============================================================
# 方式一：通过 ddgs 搜索采集（推荐，不会被封）
# ============================================================
def search_and_save(topic: str, max_results: int = 5) -> list[str]:
    """
    搜索指定主题，保存结果摘要为文档。
    返回保存的文件路径列表。
    """
    saved = []
    safe_name = re.sub(r"[^\w一-鿿]", "_", topic)[:30]

    try:
        print(f"  搜索: {topic}")
        with DDGS() as ddgs:
            results = list(ddgs.text(f"高考 {topic}", max_results=max_results))

        if not results:
            print(f"    [无结果]")
            return saved

        # 把所有结果合并为一个文档
        lines = [
            f"# 主题: {topic}",
            f"# 采集时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"# 来源: DDGS 网络搜索\n",
        ]

        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"## [{i}] {title}")
            lines.append(f"来源: {href}")
            lines.append(f"{body}\n")

        filepath = os.path.join(OUTPUT_DIR, f"search_{safe_name}.txt")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        print(f"    [保存] {filepath} ({len(results)} 条结果)")
        saved.append(filepath)

    except Exception as e:
        print(f"    [失败] {e}")

    return saved


# ============================================================
# 方式二：爬取具体网页（可能会被反爬）
# ============================================================
def fetch_page(url: str) -> str | None:
    """获取网页 HTML"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://www.google.com/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"    [请求失败] {e}")
        return None


def extract_text(html: str) -> str:
    """从 HTML 提取正文"""
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "nav", "footer", "header",
                      "noscript", "iframe", "aside"]):
        tag.decompose()

    noise = ["sidebar", "nav", "footer", "header", "ad", "banner",
             "menu", "toolbar", "comment", "recommend", "related"]
    for cls in noise:
        for tag in soup.find_all(class_=re.compile(cls, re.I)):
            tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 10]
    return "\n".join(lines)


def crawl_url(url: str) -> str | None:
    """爬取单个 URL，返回文件路径"""
    print(f"  爬取: {url}")

    html = fetch_page(url)
    if not html:
        return None

    text = extract_text(html)
    if len(text) < 100:
        print(f"    [跳过] 正文太短 ({len(text)} 字符)")
        return None

    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_") or "index"
    safe = re.sub(r"[^\w一-鿿-]", "_", path)[:50]
    filepath = os.path.join(OUTPUT_DIR, f"web_{safe}.txt")

    content = f"# 来源: {url}\n# 爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n{text}"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"    [保存] {filepath} ({len(text)} 字符)")
    return filepath


# ============================================================
# 默认搜索主题列表
# ============================================================
DEFAULT_TOPICS = [
    "平行志愿是什么意思 录取规则",
    "高考投档线 录取批次 解释",
    "高考志愿填报 冲稳保 策略技巧",
    "计算机科学与技术 专业介绍 就业前景",
    "软件工程 专业介绍 课程设置",
    "临床医学 专业介绍 培养模式",
    "电子信息工程 专业介绍 就业方向",
    "金融学 专业介绍 就业前景",
    "新高考 选科要求 专业对应",
    "高考志愿填报 常见误区 注意事项",
    "双一流 大学排名 学科评估",
    "服从调剂 退档 滑档 是什么意思",
]


# ============================================================
# 主入口
# ============================================================
if __name__ == "__main__":
    ensure_output_dir()
    args = sys.argv[1:]

    if args and args[0] == "--url":
        # 爬取指定 URL
        print(f"爬取网页: {args[1]}\n")
        crawl_url(args[1])
    else:
        # 搜索采集
        print(f"搜索采集 {len(DEFAULT_TOPICS)} 个主题\n")
        total = 0
        for i, topic in enumerate(DEFAULT_TOPICS, 1):
            print(f"[{i}/{len(DEFAULT_TOPICS)}]", end=" ")
            saved = search_and_save(topic)
            total += len(saved)
            time.sleep(REQUEST_DELAY)

        print(f"\n完成！共保存 {total} 篇文档")
        print(f"文档位置: {OUTPUT_DIR}/")
