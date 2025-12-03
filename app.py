import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import io

# --- 1. 全局配置与密钥 ---
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    GOOGLE_API_KEY = "请在Streamlit Secrets中配置你的KEY" 

# 🛠️ 模型版本设置
MODEL_VERSION = "gemini-3-pro-preview"

# --- 2. 页面初始化 ---
st.set_page_config(
    page_title="图解心灵讨论组",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- 3. 状态管理 (Session State) ---
if "auth_diagnostic" not in st.session_state:
    st.session_state.auth_diagnostic = False
if "auth_reader" not in st.session_state:
    st.session_state.auth_reader = False

# --- 4. CSS 深度视觉定制 (终极白字修正版) ---
st.markdown("""
    <style>
        /* =========================================
           1. 基础布局与侧边栏宽度
           ========================================= */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* 侧边栏容器加宽 */
        section[data-testid="stSidebar"] {
            min-width: 380px !important;
            width: 380px !important;
            background-color: #f9f9f9 !important;
            border-right: 1px solid #333333;
        }

        /* =========================================
           2. 右侧主区域 (Main Area) - 纯黑底 + 纯白字
           ========================================= */
        .stApp {
            background-color: #000000 !important;
        }
        
        /* ☢️ 核心修复 1：针对 Streamlit Cloud 的标题强制白字 ☢️ */
        .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
        .main .stHeadingContainer h1,
        .main .stHeadingContainer h2,
        .main .stHeadingContainer h3,
        .main .stHeadingContainer h4,
        .main span {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        
        /* ☢️ 核心修复 2：针对 AI 生成报告正文的强制白字 ☢️ */
        .main .stMarkdown p, 
        .main .stMarkdown li, 
        .main .stMarkdown strong, 
        .main .stMarkdown em,
        .main div[data-testid="stMarkdownContainer"] p,
        .main div[data-testid="stMarkdownContainer"] li {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }

        /* Tabs 样式 (黑底白字) */
        .stTabs { background-color: #000000; }
        .stTabs [data-baseweb="tab-list"] { background-color: #000000; gap: 20px; }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            border: none !important;
        }
        .stTabs [data-baseweb="tab"] p {
            color: #aaaaaa !important; 
        }
        .stTabs [aria-selected="true"] p {
            color: #ffffff !important;
            font-weight: bold;
        }
        .stTabs [aria-selected="true"] {
            border-bottom: 2px solid #ffffff !important;
        }

        /* ☢️ 核心修复 3：按钮样式 (白底黑字) ☢️ */
        .stButton > button {
            width: 100%;
            border-radius: 0px !important;
            border: 1px solid #ffffff !important;
            background-color: #ffffff !important; /* 白底 */
            padding: 12px;
            transition: all 0.3s ease;
        }

        /* 🚨 强制按钮内的所有层级文字为黑色 🚨 */
        .stButton > button, 
        .stButton > button *, 
        .stButton > button p {
            color: #000000 !important; /* 黑字 */
            font-weight: 600 !important;
        }
        
        .stButton > button:hover {
            background-color: #f0f0f0 !important;
            border-color: #ffffff !important;
        }
        
        /* 主区域输入框 */
        .main input {
            background-color: #1a1a1a !important;
            border: 1px solid #444444 !important;
            color: #ffffff !important;
        }
        
        .main div[data-testid="stTextInput"] label p {
            color: #cccccc !important; 
            font-size: 14px !important;
        }
        
        /* =========================================
           3. 左侧边栏 (Sidebar) - 浅灰底 + 深色字
           ========================================= */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h1 span {
            color: #000000 !important;
        }
        
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] .stCaption, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] div {
            color: #000000 !important; 
        }
        
        [data-testid="stSidebar"] input {
            background-color: #ffffff !important;
            border: 1px solid #cccccc !important;
            min-height: 36px;
            color: #000000 !important; 
            caret-color: #cccccc !important; 
        }
        
        [data-testid="stSidebar"] input:disabled {
            background-color: #eeeeee !important;
            color: #999999 !important;
        }
        
        [data-testid="stSidebar"] label[data-baseweb="checkbox"] {
            white-space: nowrap; 
        }
        
        [data-testid="stSidebar"] [data-baseweb="checkbox"] div {
             color: #000000 !important;
        }

    </style>
""", unsafe_allow_html=True)

# --- 5. System Prompts ---

PROMPT_DIAGNOSTIC = """
# System Role: 艺术分析学者

## 核心定位
你是一个**“拼命想要读懂这幅画的全知学者”**。
你拥有百科全书般的知识库（历史、物理、心理、认知科学、行为科学、艺术史、符号学、生物学、生理学等等），但你**不堆砌术语**。你将这些知识内化为一种**强烈的求知欲**。你通过不断的**“提问-解答”**（Self-Correction & Chain of Thought），带领读者一层层剥开画作的表象。

你的语言风格应该是**通俗、流畅、具有极强的画面感和代入感**。不仅要告诉读者“有什么”，更要解释“为什么是这样”。禁止使用“不是...而是...”句式。直接断言“是什么”。多用动词。

---

## 写作逻辑与结构 

*只输出两行，精准定义。*

* **原型**：（判定标准：指涉跨文化、跨时代反复出现的深层意义结构，其特征是普遍性、抽象性与心理经验的稳定性，不依赖单一文化语境。限7字以内。）
* **意象**：（判定标准：属于特定文化与文本内部的符号单位，其意义由具体语境、历史传统与作品内部的视觉结构决定，具有特指性与语境依赖性。提取5个病灶细节。）

接着，请严格按照以下**四个层级**，由远及近，由大到小，层层递进地撰写分析。这部分至少要1300字。

### 第一层：时代的风暴眼 
* **焦点**：**创作年份与地点**。
* **思维链**：把时间轴拨回到那一年。那时候发生了什么历史大事件？那时候的空气里弥漫着什么味道（焦虑、狂欢、压抑？）当时流行什么样的思潮？
* **核心任务**：解释这幅画为什么**必须**诞生在这个时间点？它承载了怎样的集体记忆或时代情绪？它是时代的镜子，还是时代的叛逆者？
* **[段落注脚]**：本段主旨：（一句话概括本段阐述的时代背景与画作的必然联系）。

### 第二层：画家的排兵布阵 
* **焦点**：**构图、几何与视线**。
* **思维链**：画家为什么要这样安排画面？为什么主要物体在左边而不是右边？是否存在某种隐藏的几何结构（螺旋、金字塔、对角线）？这是一种视觉上的引导，还是一种心理上的压迫？
* **核心任务**：分析画面的“骨架”。这不只是美学，这是画家操控观众视线的“战术”。
* **[段落注脚]**：本段主旨：（一句话概括画家通过构图想要达到的视觉引导或心理暗示）。

### 第三层：静物 
* **焦点**：**画中的物品/背景细节**。
* **思维链**：不要把物体当成静止的。每一个物体都有它的过去、现在和未来。
    * *过去*：这个物体之前遭遇了什么？为什么它会破损/崭新？
    * *现在*：它在画面中起什么作用？它在暗示什么？
    * *未来*：下一秒它会掉落吗？会枯萎吗？
* **核心任务**：钻进画里，让静止的物体流动起来。挖掘物体背后的隐喻（例如：一盏将熄的灯暗示了什么？一块凌乱的地毯藏着什么秘密？）。
* **[段落注脚]**：本段主旨：（一句话概括画中物品所承载的叙事功能或象征意义）。

### 第三层：人物与关系
* **焦点**：**人物（或拟人化的主体）**。
* **思维链**：这是最核心的部分。对人物进行“里里外外、上上下下”的打量。
    * *外观*：为什么穿这件衣服？（材质、阶级、时尚史）。为什么头发是乱的？
    * *动作*：为什么手是这个姿势？他在防御还是在索取？
    * *神情*：他的眼神看向哪里？他在回避什么？
    * *关系*：如果有多人，他们之间的距离代表了什么？谁掌握权力？
* **核心任务**：通过不断的**“为什么”**，推导出人物的心理状态、社会地位以及他此刻正在经历的内心风暴。
* **[段落注脚]**：本段主旨：（一句话概括人物的心理状态或角色定位）。

---

## 最后的总结 (The Final Insight)
基于以上四层的层层剥离，给出一个简短有力的提问。将读者的情绪从画中拉回到现实，引发思考。

---

## 交互指令
请等待用户输入【艺术作品名称】+【创作年份】（可选）。
一旦接收，立即启动“全知学者”模式，开始那场从宏观历史到微观灵魂的深度旅程。
"""

PROMPT_READER = """
Role: 艺术侦探与文化解读者
你是一位不仅精通艺术史，更擅长用精准、笃定的中文进行叙事的艺术解读者。你的语言风格洗练、老辣，杜绝一切廉价的口语（如“然后”、“那个”），也拒绝生硬的翻译腔。你的核心任务是挖掘画作的绝对独特性，并基于事实给出有信息增量的解读。

核心思维模型：独特性光谱 (The Uniqueness Model)
在开始写作前，请先在内心对画作进行“独特性定位”，并据此调整你的叙述策略（不要把思考过程写出来，直接体现在最终文风中）：

如果是叙事型作品（如历史画、风俗画）：策略侧重于“导演视角”，聚焦瞬间的戏剧张力、人物关系的微表情、背景中潜藏的线索。

如果是情绪/氛围型作品（如印象派、抽象表现主义）：策略侧重于“通感修辞”，用温度、触觉、听觉的词汇来翻译视觉色彩。

如果是技法/结构型作品（如立体主义、构成主义）：策略侧重于“解剖视角”，拆解其空间逻辑、线条的暴力或秩序。

严格语言禁令 (Negative Constraints)
绝对禁止使用“不是……而是……”句式（以及类似的“非……乃……”、“与其说……不如说……”）。

错误示范：这种红不是鲜艳的红，而是像血一样的暗红。

正确示范：这种红像干涸的血迹一样暗沉。

原则：直陈其事。只描述它是什么。

拒绝万能模板。不要用“这幅画展示了……”、“通过这幅画我们可以看到……”这种套话。直接切入画面。

事实洁癖。每一处关于背景、生平、隐喻的解读，必须有事实出处（可参考博物馆档案、书信集、传记）。若某处信息模糊或存疑，直接删去该部分，绝不进行“合理的猜测”或强行自圆其说。

输出栏目要求 (Output Sections)
请严格按照以下四个栏目进行撰写，内容需详实且富于变化：

01. 作画的人
溯源：用确凿的证据定位画家的身份坐标。引用他/她同时代人的评价，或他/她自己的信件原话来佐证其性格。

执念：他/她这辈子最放不下的那个“母题”是什么？（例如：光线、死亡、某种特定的脸型）。

此时此地：创作这幅画的具体年份，画家正处于什么样的人生境遇中？（是落魄潦倒、春风得意，还是病痛缠身？）请提供具体的传记细节，而非笼统的“创作高峰期”。

02. 画里乾坤
直击感官：根据前述的“独特性模型”定调。如果是风景，讲气温和湿度；如果是肖像，讲眼神的压迫感或闪躲。

证据链：按视觉逻辑扫描画面。不要罗列物体，要描述物体之间的“张力”。

显微镜：找出画面中容易被忽略的1-2个细节（角落的杂物、手指的弯曲度、反光中的倒影），并直接指出其物理形态。

03. 门道拆解
技术指纹：这幅画最独特的“技术特征”是什么？是笔触的厚度？是构图的失衡？还是光线的悖论？

去形容词化：不要说“高超的技巧”，要说“他用刮刀代替画笔堆叠出了岩石的质感”或“他故意拉长了人物的脊椎以制造不稳定性”。

行业标准：用艺术行业的专业维度（如明暗对照法 Chiaroscuro、晕涂法 Sfumato、固有色与环境色关系等）来解释画面效果，解释要通俗但原理要硬核。

04. 看画小记
逻辑闭环：将“作画的人”的遭遇与“画里乾坤”的细节，用一条事实逻辑线串联起来。

祛魅与评价：客观评估这幅画在画家生涯中的真实地位。它是一次完美的成功，还是一次有缺憾的实验？依据是什么？

终极定性：用一句话总结这幅画的“物理存在感”或“精神重量”，言简意赅，掷地有声。

User Input: 艺术作品名称：{{Title}} 艺术家：{{Artist}} 创作年份：{{Year}}
"""

# --- 6. 辅助函数 ---
def load_image_from_url(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content))
        return image
    except Exception as e:
        st.error(f"图片加载失败: {e}")
        return None

# --- 7. 侧边栏逻辑 ---
with st.sidebar:
    st.markdown("### 模式选择")
    mode = st.radio(
        "Select Mode",
        ["图解心灵讨论组", "漫游艺术领读人"], 
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 鉴权状态判断
    is_unlocked = False
    if mode == "图解心灵讨论组" and st.session_state.auth_diagnostic:
        is_unlocked = True
    elif mode == "漫游艺术领读人" and st.session_state.auth_reader:
        is_unlocked = True
    
    # 全局禁用开关
    global_disable = not is_unlocked

    st.markdown("### 档案录入")
    
    # --- A. 艺术家输入 ---
    st.caption("艺术家")
    col_a1, col_a2 = st.columns([3, 1])
    
    with col_a2:
        unknown_artist = st.checkbox("未知", key="chk_artist", disabled=global_disable)
    with col_a1:
        artist_disabled = global_disable or unknown_artist
        
        if unknown_artist:
            artist_name = "未知"
            st.text_input("Artist", value="未知", disabled=True, label_visibility="collapsed", key="input_artist_dis")
        else:
            artist_name = st.text_input("Artist", placeholder="如: 弗朗西斯·培根", disabled=artist_disabled, label_visibility="collapsed", key="input_artist")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- B. 作品名输入 ---
    st.caption("作品名称")
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
         artwork_title = st.text_input("Title", placeholder="如: 肖像习作", disabled=global_disable, label_visibility="collapsed")
    with col_t2:
        st.empty()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- C. 年份输入 ---
    st.caption("创作年份")
    col_y1, col_y2 = st.columns([3, 1])
    
    with col_y2:
        unknown_year = st.checkbox("未知", key="chk_year", disabled=global_disable)
    with col_y1:
        year_disabled = global_disable or unknown_year
        
        if unknown_year:
            artwork_year = "未知"
            st.text_input("Year", value="未知", disabled=True, label_visibility="collapsed", key="input_year_dis")
        else:
            artwork_year = st.text_input("Year", placeholder="如: 1953", disabled=year_disabled, label_visibility="collapsed", key="input_year")
    
    st.markdown("---")
    
    # 系统状态栏
    st.caption("系统状态") 
    status_val = "WAITING FOR AUTH..." if global_disable else "CORE MODULE LOADED"
    st.text_input("Auth", value=status_val, disabled=True, label_visibility="collapsed")


# --- 8. 主界面逻辑 ---

# 动态标题逻辑
if mode == "图解心灵讨论组":
    st.title("图解心灵讨论组")
else:
    st.title("漫游艺术领读人")

# 鉴权逻辑分支
if not is_unlocked:
    # --- 锁定状态界面 (Main Area) ---
    st.divider()
    st.markdown("### 权限验证")
    
    # 纯白提示语
    current_mode_text = mode if mode == '漫游艺术领读人' else '图解心灵讨论组'
    st.markdown(f"您正在尝试访问 **{current_mode_text}**，请输入访问密钥。")
    
    password_input = st.text_input("输入密钥", type="password", key="pwd_input")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    unlock_btn = st.button("解锁终端")
    
    if unlock_btn:
        if mode == "图解心灵讨论组" and password_input == "0006":
            st.session_state.auth_diagnostic = True
            st.rerun()
        elif mode == "漫游艺术领读人" and password_input == "4666":
            st.session_state.auth_reader = True
            st.rerun()
        else:
            st.error("密钥错误，访问被拒绝。")

else:
    # --- 解锁状态界面 (功能区) ---
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 艺术作品上传")
    
    tab1, tab2 = st.tabs(["本地上传", "网络链接"])
    uploaded_image = None

    with tab1:
        file = st.file_uploader("选择文件", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if file:
            uploaded_image = Image.open(file)

    with tab2:
        url = st.text_input("粘贴图片 URL", label_visibility="collapsed", placeholder="http://...")
        if url:
            uploaded_image = load_image_from_url(url)

    # 图片预览
    if uploaded_image:
        st.image(uploaded_image, use_column_width=True)
    else:
        st.markdown("""
        <div style="background-color: #111111; height: 150px; display: flex; align-items: center; justify-content: center; color: #555555; border: 1px dashed #333333; margin-top: 10px; font-size: 0.8rem;">
            等待影像输入...
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 执行按钮 (白底黑字)
    if st.button("启动"):
        if not GOOGLE_API_KEY or "配置" in GOOGLE_API_KEY:
            st.error("系统错误: API Key 无效或未配置。")
            st.stop()
        
        if not uploaded_image:
            st.warning("请先上传图片或输入图片链接。")
            st.stop()

        # 配置 API
        genai.configure(api_key=GOOGLE_API_KEY)
        
        current_title = artwork_title if artwork_title else "未知作品"
        current_artist = artist_name if artist_name else "未知艺术家"
        current_year = artwork_year if artwork_year else "未知年份"

        # --- 指令分发 ---
        if mode == "图解心灵讨论组":
            # 诊断间逻辑
            dynamic_instructions = ""
            if unknown_artist:
                dynamic_instructions += "\n⚠️ 艺术家身份未知，请忽略背景分析，强制执行盲测模式。"
            if unknown_year:
                dynamic_instructions += "\n⚠️ 创作年份未知，请跳过宏观历史分析，仅推测可能的年代感。"

            # 🛠️ 核心修复：在 User Prompt 中强制注入元数据，防止 AI 忽视输入
            user_prompt_content = f"""
            [绝对事实/GROUND TRUTH]
            请务必以以下元数据为准，不要基于视觉相似性猜测其他艺术家。
            
            艺术家: {current_artist}
            作品名: {current_title}
            年份: {current_year}
            
            {dynamic_instructions}
            
            请基于 System Instruction 中的角色设定，对这张图片进行深度分析。
            """
            
            final_system_prompt = PROMPT_DIAGNOSTIC

        else:
            # 领读人逻辑
            
            # 1. 替换 System Prompt 中的占位符 (双重保险)
            final_system_prompt = PROMPT_READER.replace("{{Title}}", current_title)
            final_system_prompt = final_system_prompt.replace("{{Artist}}", current_artist)
            final_system_prompt = final_system_prompt.replace("{{Year}}", current_year)
            
            # 🛠️ 核心修复：在 User Prompt 中也强制注入元数据，因为 Gemini 更听从 User Prompt
            user_prompt_content = f"""
            请针对以下作品开始解读：
            艺术家：{current_artist}
            作品名：{current_title}
            年份：{current_year}

            请严格基于上述信息进行分析，不要质疑或更改艺术家身份。
            """

        # AI 生成与流式输出
        st.divider()
        st.markdown("### 分析报告")
        report_placeholder = st.empty()
        full_response = ""

        try:
            model = genai.GenerativeModel(
                model_name=MODEL_VERSION,
                system_instruction=final_system_prompt
            )
            
            response_stream = model.generate_content(
                [user_prompt_content, uploaded_image],
                stream=True
            )
            
            for chunk in response_stream:
                if chunk.text:
                    full_response += chunk.text
                    report_placeholder.markdown(full_response + "▌")
            
            report_placeholder.markdown(full_response)

        except Exception as e:
            st.error(f"运行时错误: {str(e)}")
