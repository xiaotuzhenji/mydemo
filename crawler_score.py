"""
专业级分数线爬虫 —— 基于掌上高考公开 API（旧版接口，数据结构更全）

数据来源: static-data.gaokao.cn
用法:
  python crawler_score.py               → 采集全部数据
  python crawler_score.py --test        → 测试模式
  python crawler_score.py --top50       → 采集前50所大学
"""
import os, csv, time, sys, re, requests

# ============================================================
# 配置
# ============================================================
OUTPUT_PATH = "data/scores_detail.csv"
DELAY = 0.15  # API 请求间隔

YEARS = [2024, 2023, 2022]

# 行政编码 → 省份名（gbk 编码的省份名）
PROVINCE_IDS = {
    33: "浙江", 11: "北京", 31: "上海", 44: "广东", 32: "江苏",
    51: "四川", 42: "湖北", 37: "山东", 41: "河南", 43: "湖南",
    35: "福建", 34: "安徽", 61: "陕西", 50: "重庆",
}

# type 编码
TYPES = {1: "理科", 2: "文科"}


# ============================================================
# API
# ============================================================
def get_school_list() -> list:
    """获取所有大学 ID 和名称"""
    url = "https://static-data.gaokao.cn/www/2.0/info/linkage.json"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.gaokao.cn/"}
    resp = requests.get(url, headers=headers, timeout=30)
    data = resp.json()
    schools = data.get("data", {}).get("school", [])
    result = []
    for s in schools:
        sid = s.get("school_id", "")
        name = s.get("name", "")
        if sid and name:
            result.append((str(sid), name))
    return result


def get_school_scores(school_id: str, year: int, province_id: int) -> list[dict]:
    """
    获取某大学在指定年份、省份的全部专业录取数据。

    API: static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{province_id}.json
    返回: [{专业, 年份, 最低分, 最低位次, 文理科}, ...]
    """
    url = f"https://static-data.gaokao.cn/www/2.0/schoolspecialscore/{school_id}/{year}/{province_id}.json"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.gaokao.cn/"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        data = resp.json()

        if data.get("code") != "0000":
            return []

        rows = []
        province_name = PROVINCE_IDS.get(province_id, str(province_id))

        # data.data 下按 type_batch 分组
        for group_key, group_val in data.get("data", {}).items():
            items = group_val.get("item", [])
            for item in items:
                # 从 info 字段提取专业名，格式如 "（计算机类，本科）"
                info = item.get("info", "")
                major = _extract_major(info)

                score = item.get("min", "")
                rank_val = item.get("min_section", "")

                # 确定文理科
                type_code = int(item.get("type", "1"))
                subject = TYPES.get(type_code, "未知")

                if score and str(score).replace(".", "").isdigit():
                    rows.append({
                        "大学": "",  # 后面填充
                        "省份": province_name,
                        "年份": year,
                        "专业": major,
                        "最低分": int(float(score)),
                        "最低位次": rank_val if rank_val != "-" else "",
                        "文理科": subject,
                    })

        return rows

    except Exception as e:
        print(f"    [错误] {school_id}/{year}/{province_id}: {e}")
        return []


def _extract_major(info: str) -> str:
    """从 info 字段提取专业名"""
    # info 格式: "（专业名，本科）" 或 "专业名（方向）"
    # 尝试多种模式
    patterns = [
        r"（(.+?)，",          # （计算机类，本科）
        r"（(.+?)\)",          # （计算机类)
        r"(.+?)（",            # 计算机类（
    ]
    for p in patterns:
        m = re.search(p, info)
        if m:
            return m.group(1).strip()
    return info if len(info) < 30 else info[:30]


# ============================================================
# 采集主逻辑
# ============================================================
def crawl():
    print("=" * 55)
    print("  高考专业级分数线采集（gaokao.cn API）")
    print("=" * 55)

    # 获取学校列表
    print("\n[1/3] 获取学校列表...")
    schools = get_school_list()
    print(f"  共 {len(schools)} 所院校")

    # 筛选：过滤职业院校
    valid = []
    for sid, name in schools:
        skip_words = ["职业", "专科", "技术学院", "职业技术"]
        if not any(w in name for w in skip_words):
            valid.append((sid, name))

    schools = valid
    print(f"  有效院校: {len(schools)} 所")

    # 取前 N 所（可配置）
    top_n = 300
    schools = schools[:top_n]
    print(f"  本次采集: 前 {len(schools)} 所")

    # 开始采集
    province_ids = list(PROVINCE_IDS.keys())
    print(f"\n[2/3] 开始采集...")
    print(f"  年份: {YEARS}")
    print(f"  省份: {list(PROVINCE_IDS.values())} ({len(province_ids)}个)")
    print(f"  预计请求: {len(schools)} × {len(YEARS)} × {len(province_ids)} = {len(schools) * len(YEARS) * len(province_ids)} 次")
    print()

    all_rows = []
    start_time = time.time()

    for i, (sid, sname) in enumerate(schools, 1):
        if i % 10 == 0:
            elapsed = time.time() - start_time
            eta = elapsed / i * (len(schools) - i)
            print(f"  [{i}/{len(schools)}] 已采集 {len(all_rows)} 条，"
                  f"耗时 {elapsed:.0f}s，预计剩余 {eta:.0f}s")

        for year in YEARS:
            for pid in province_ids:
                rows = get_school_scores(sid, year, pid)
                for r in rows:
                    r["大学"] = sname
                all_rows.extend(rows)
                time.sleep(DELAY)

    # 保存
    print(f"\n[3/3] 保存数据...")
    if all_rows:
        with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["大学","省份","年份","专业","最低分","最低位次","文理科"])
            writer.writeheader()
            writer.writerows(all_rows)

        univs = set(r["大学"] for r in all_rows)
        provs = set(r["省份"] for r in all_rows)
        yrs = sorted(set(str(r["年份"]) for r in all_rows))
        with_rank = sum(1 for r in all_rows if r["最低位次"] and r["最低位次"] != "-")
        print(f"  保存到: {OUTPUT_PATH}")
        print(f"  共 {len(all_rows)} 条记录 | {len(univs)} 所大学 | {len(provs)} 省 | {yrs} 年")
        print(f"  含位次数据: {with_rank}/{len(all_rows)} ({with_rank/len(all_rows)*100:.0f}%)")
    else:
        print("  未采集到数据！")

    elapsed = time.time() - start_time
    print(f"\n总耗时: {elapsed:.0f} 秒 ({elapsed/60:.1f} 分钟)")


if __name__ == "__main__":
    if "--test" in sys.argv:
        # 测试模式
        print("=== 测试模式 ===")
        rows = get_school_scores("140", 2023, 33)
        print(f"清华 / 2023 / 浙江: {len(rows)} 个专业")
        for r in rows[:5]:
            print(f"  {r['专业']}: {r['最低分']}分, 位次={r['最低位次']}, {r['文理科']}")
    else:
        crawl()
