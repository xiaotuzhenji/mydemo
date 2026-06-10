"""
高考志愿填报助手 - Demo（流式输出）
运行：.venv\Scripts\streamlit run app.py
"""
import os, json, glob
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.callbacks import BaseCallbackHandler
from langchain.agents import create_agent
from tools import TOOLS

load_dotenv()

# ============================================================
# 0. 页面配置
# ============================================================
st.set_page_config(page_title="高考志愿填报助手", page_icon="🎓", layout="wide")

# ============================================================
# 1. 流式回调处理器
# ============================================================
class StreamHandler(BaseCallbackHandler):
    """捕获 LLM 输出的每个 token，实时显示到 Streamlit"""

    def __init__(self, container, initial_text=""):
        self.container = container
        self.text = initial_text
        self.first_token = False

    def on_llm_new_token(self, token: str, **kwargs):
        if not self.first_token:
            self.first_token = True
        self.text += token
        self.container.markdown(self.text + " ▌")

    def on_llm_end(self, response, **kwargs):
        self.container.markdown(self.text)


# ============================================================
# 2. 记忆系统
# ============================================================
CHATS_DIR = "chats"

def ensure_chats_dir():
    if not os.path.exists(CHATS_DIR): os.makedirs(CHATS_DIR)

def save_chat(fpath, msgs):
    ensure_chats_dir()
    data = {
        "messages": [{"role": type(m).__name__, "content": m.content}
                     for m in msgs if isinstance(m, (HumanMessage, AIMessage))],
        "updated_at": datetime.now().isoformat(),
    }
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat(fpath):
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    msgs = []
    for m in data.get("messages", []):
        if m["role"] == "HumanMessage": msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "AIMessage": msgs.append(AIMessage(content=m["content"]))
    return msgs

def list_chats():
    ensure_chats_dir()
    files = sorted(glob.glob(f"{CHATS_DIR}/*.json"), reverse=True)
    result = []
    for f in files:
        name = os.path.basename(f).replace(".json", "")
        try:
            with open(f, "r", encoding="utf-8") as fp: data = json.load(fp)
            cnt = len(data.get("messages", []))
            updated = data.get("updated_at", "?")[:16]
            preview = ""
            for m in data.get("messages", []):
                if m["role"] == "HumanMessage": preview = m["content"][:25]; break
            result.append((name, cnt, updated, preview))
        except Exception: pass
    return result

def new_chat_filepath():
    ensure_chats_dir()
    return f"{CHATS_DIR}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

# ============================================================
# 3. 初始化 Agent（LLM 开启流式）
# ============================================================
@st.cache_resource
def get_agent():
    llm = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
        temperature=0.3,
        streaming=True,  # ← 开启流式输出
    )
    return create_agent(model=llm, tools=TOOLS, system_prompt="")

agent_graph = get_agent()

# ============================================================
# 4. 会话状态
# ============================================================
for key, default in [
    ("messages", []), ("current_file", None), ("chat_loaded", False),
    ("profile_set", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ============================================================
# 5. 侧边栏
# ============================================================
with st.sidebar:
    st.title("🎓 高考志愿助手")

    # ---- 用户画像 ----
    if st.session_state.get("profile_set"):
        st.success(f"📍 {st.session_state.get('profile_province','')} | "
                   f"{st.session_state.get('profile_score','')}分 | "
                   f"{st.session_state.get('profile_subject','')}")
        st.caption(f"🏙 {st.session_state.get('profile_city','不限')}")
        if st.button("✏ 修改信息", use_container_width=True):
            st.session_state.profile_set = False
            st.rerun()
    else:
        st.warning("👆 先填信息，再问问题")
        province = st.selectbox("省份", ["浙江","北京","上海","广东","江苏","四川","山东",
                                          "湖北","湖南","河北","河南","天津","陕西","其他"])
        score = st.number_input("分数/预估分", 0, 750, 600, step=5)
        subject = st.selectbox("选科", ["理科/物理类","文科/历史类","综合/不分科"])
        city = st.text_input("意向城市（选填）", placeholder="如：杭州、上海")
        if st.button("💾 保存，开始咨询", use_container_width=True):
            st.session_state.profile_set = True
            st.session_state.profile_province = province
            st.session_state.profile_score = score
            st.session_state.profile_subject = subject
            st.session_state.profile_city = city or "不限"
            st.session_state.user_profile = (
                f"【重要】用户是{province}考生，{subject}，预估{score}分，意向城市：{city or '不限'}。"
                f"所有推荐和建议必须基于此考生信息，不要说'如果你是什么省份'这种假设性的话。"
            )
            st.rerun()

    st.divider()

    if st.button("＋ 新建对话", use_container_width=True):
        if st.session_state.current_file:
            save_chat(st.session_state.current_file, st.session_state.messages)
        st.session_state.messages = []
        st.session_state.current_file = new_chat_filepath()
        st.session_state.chat_loaded = False
        save_chat(st.session_state.current_file, st.session_state.messages)
        st.rerun()

    with st.expander("💬 历史对话"):
        chats = list_chats()
        if not chats:
            st.caption("暂无")
        for name, cnt, updated, preview in chats:
            is_current = st.session_state.current_file == f"{CHATS_DIR}/{name}.json"
            label = f"● {preview}" if is_current else preview or updated
            if st.button(label[:35], key=name, use_container_width=True):
                if st.session_state.current_file:
                    save_chat(st.session_state.current_file, st.session_state.messages)
                st.session_state.messages = load_chat(f"{CHATS_DIR}/{name}.json")
                st.session_state.current_file = f"{CHATS_DIR}/{name}.json"
                st.session_state.chat_loaded = True
                st.rerun()

# ============================================================
# 6. 系统提示词
# ============================================================
profile_text = st.session_state.get("user_profile", "")

no_profile_rule = (
    '用户尚未提供画像。'
    '当用户问及推荐/选学校/选专业/能不能上等需要个人情况的问题时，'
    '必须先反问：哪个省的？多少分？理科还是文科？家里做什么的？'
    '不拿到这些信息不给具体建议。'
)

SYSTEM_PROMPT = f"""你是高考志愿填报助手。{profile_text}

你有五个工具：
1. query_admission_score: 查48所重点大学的本地专业级分数线（2024+2023，含位次）
2. query_live_score: 实时查近3000所大学的专业级分数线（掌上高考API）
3. web_search: 联网搜索最新招生政策、专业前景、行业趋势
4. query_knowledge_base: 查概念解释、填报策略、专业介绍
5. check_employment: 查大学毕业生真实就业去向、雇主、500强招聘情况

工具选择：
- 分数线/位次 → 优先 query_admission_score，没有的用 query_live_score
- 概念/策略/专业介绍 → query_knowledge_base
- 最新政策/实时信息 → web_search
- 就业去向/雇主 → check_employment

== 核心工作原则 ==

[先查数据再开口]
涉及具体学校/专业/就业的问题，必须先调工具查数据。凭记忆回答就是骗人。

[灵魂追问 - 没有画像先别答]
{profile_text if profile_text else no_profile_rule}

[回答框架]
- 第一句就给明确判断，不要铺垫"这个问题比较复杂"
- 用中位数原则：不看前3%天才的年薪，看中间50%毕业生去了哪
- 做不可替代性检验：AI能替代这个岗位吗？能被替代的慎重推荐
- 区分家庭背景：有资源的家庭和普通家庭的策略完全不同
- 城市优先：同分数段优先推荐发达城市，机会不是一个量级

[表达风格]
- 直接、肯定、给判断不废话
- 引用具体数据（分数线、位次、薪资），不说"前景不错"这种空话
- 每次不超过3段，每段不超过4句"""

if not st.session_state.get("profile_set"):
    SYSTEM_PROMPT += """
[特别指令：用户信息缺失]
如果用户的问题涉及推荐/选学校/选专业/能不能上等需要结合个人情况的判断，
必须先反问用户获取：省份、分数、文理科、家庭资源。不拿到这些不给出具体建议。"""

# ============================================================
# 7. 主区域
# ============================================================
st.title("🎓 高考志愿填报助手")
st.caption("181所大学 · 13省数据 · AI驱动 · 实时联网 · 流式输出")

# 首次加载
if not st.session_state.chat_loaded:
    if st.session_state.current_file is None:
        ensure_chats_dir()
        files = sorted(glob.glob(f"{CHATS_DIR}/*.json"), reverse=True)
        if files:
            st.session_state.messages = load_chat(files[0])
            st.session_state.current_file = files[0]
        else:
            st.session_state.current_file = new_chat_filepath()
            save_chat(st.session_state.current_file, st.session_state.messages)
    st.session_state.chat_loaded = True

# ---- 快捷提问 ----
if len(st.session_state.messages) == 0:
    st.subheader("💡 试试这些问题")
    suggestions = [
        "平行志愿的投档规则是什么？",
        "冲稳保策略怎么分配比较合理？",
        "计算机专业就业前景怎么样？",
        "服从调剂是什么意思，要不要勾选？",
    ]
    if st.session_state.get("profile_set"):
        suggestions.insert(0, "我这个分数能上什么大学？")
    cols = st.columns(len(suggestions))
    for i, (col, sug) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state._quick_input = sug
                st.rerun()

# 渲染历史
for msg in st.session_state.messages:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"): st.write(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant", avatar="🎓"): st.write(msg.content)

# ---- 输入处理 ----
quick = st.session_state.pop("_quick_input", None)
user_input = quick or st.chat_input(
    "输入你的问题..." if st.session_state.messages else "随便问，比如「600分在浙江能上什么大学」..."
)

if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append(HumanMessage(content=user_input))

    with st.chat_message("assistant", avatar="🎓"):
        # 创建一个占位容器，流式写入
        placeholder = st.empty()
        stream_handler = StreamHandler(placeholder)

        try:
            full_messages = [HumanMessage(content=f"[系统指令]\n{SYSTEM_PROMPT}")]
            full_messages.extend(st.session_state.messages)

            # invoke + callbacks 实现流式输出
            result = agent_graph.invoke(
                {"messages": full_messages},
                config={"callbacks": [stream_handler]},
            )

            # 确保最终文本写入
            final_answer = ""
            for m in reversed(result["messages"]):
                if isinstance(m, AIMessage) and m.content:
                    final_answer = m.content
                    break

            # 如果流式没触发（比如只有工具调用），fallback 显示最终答案
            if not stream_handler.first_token:
                placeholder.markdown(final_answer)

            st.session_state.messages.append(AIMessage(content=final_answer))

        except Exception as e:
            st.error(f"调用失败: {e}")
            st.session_state.messages.pop()

    if st.session_state.current_file:
        save_chat(st.session_state.current_file, st.session_state.messages)
    st.rerun()
