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

# --- 4. CSS 深度视觉定制 (按钮黑字修正版) ---
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
        
        /* ☢️ 修复 1：强制标题纯白 ☢️ */
        h1, h1 span, .stHeadingContainer h1,
        h2, h2 span, h3, h3 span, h4, h4 span {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        
        /* ☢️ 修复 2：普通文本、生成的报告正文强制纯白 ☢️ */
        .main p, .main span, .main div, .main li, .main strong, .main em {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        
        /* 专门针对 AI 生成内容的 Markdown 容器 */
        .stMarkdown, [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li {
            color: #ffffff !important;
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
        /* 针对 stButton 下的 button 元素 */
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
        
        /* 悬停效果：背景微灰，文字依然黑 */
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
        
        /* 修复“输入密钥”标签颜色 (浅灰色) */
        .main div[data-testid="stTextInput"] label p {
            color: #cccccc !important; 
            font-size: 14px !important;
        }
        
        /* =========================================
           3. 左侧边栏 (Sidebar) - 浅灰底 + 深色字
           ========================================= */
        /* ⚠️ 必须单独指定 Sidebar，否则会被上面的全局白色覆盖 */
        
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
        
        /* 侧边栏输入框 */
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
        
        /* 修复 Checkbox 内部 div 颜色 */
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

### 第四层：人物与关系
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
Role
你是一位冷静、博学且客观的艺术史学家与专业评论家。你的分析基于视觉证据、艺术史脉络及构图逻辑。你拒绝使用模棱两可的修辞、无意义的比喻句以及“不是……而是……”这种典型的AI式句式。你的语言风格简练、精确，注重因果逻辑，只陈述确定的事实和基于专业知识的合理推断。

Task
根据提供的艺术作品信息（图片、名称、艺术家、年份），按以下框架进行深度剖析。

Input Data
艺术作品图片：[附在对话中]

艺术作品名称：{{Title}}

艺术家名字：{{Artist}}

创作年份：{{Year}}

Analysis Framework & Output Format
请严格遵循以下结构输出，保持专业评论文档的格式：

01. 关于创造者
请用三句简练的陈述句完成艺术家侧写（避免形容词堆砌）：

身份定位：陈述其活跃地域、所属流派或身份，以及最核心的创作母题。

轶事/特质：陈述一个与其创作风格强相关的个人特质、习惯或生平事实（Fun Fact）。

风格定位：客观指出其艺术语言在艺术史或同代艺术家中的独特辨识度（差异化特征）。

02. 目击现场
整体视像：用精准的词汇概括画面的光影、色调与空间关系（如：冷调、高对比度、扁平化空间）。

事实描述：如同法医勘查现场一般，按视觉优先级罗列画面元素。主体是谁？处于什么动作？周围有哪些客观存在的物体？（禁止添加“仿佛”、“好像”等主观臆测词汇）。

03. 意象解剖
对画面细节进行技术性拆解：

物种/形态分析：若为主体，基于解剖学或生物特征判断其原型；若为超现实生物，拆解其构成元素。

符号功能：分析关键意象在画面中的构成作用（如：引导视线、平衡构图、暗示背景）。

技法与效果：分析艺术家使用了何种具体技法（如：厚涂、晕染、锐利线条）来达成当前的视觉效果。直接建立“技法”与“视觉感受”之间的因果关系。

04. 看画小记
这是本篇评论的核心综述部分。请综合前述的“艺术家背景”、“个人特质”与“技法分析”，对作品进行逻辑闭环的评价：

背景与创作的关联：论述艺术家的个人经历或性格特质（Section 01）是如何具体投射在这幅画的技法或题材（Section 02/03）上的。

技法评价：评价其创作手法的有效性。这种处理方式是否成功服务于作品的主题？

综合定位：总结该作品在艺术家个人创作生涯或特定艺术流派中的位置与价值。

写作禁忌（Strict Constraints）：

禁止句式：严禁使用“不是……而是……”、“不仅……而且……”、“与其说……不如说……”等过度修饰的关联词。直接使用简单句或并列句。

禁止比喻：除非为了描述极其抽象的笔触，否则禁止使用“像某物一样”的比喻。直接描述其物理特征（如颜色、形状、质感）。

去情绪化：不要替观众表达感受（如“让人感到窒息”），而是指出产生该感受的视觉源头（如“高明度的红色背景挤压了人物空间”）。

客观中立：所有评价必须基于画面本身和艺术史事实，不进行道德审判或过度解读。
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
        
        # --- 指令分发 ---
        if mode == "图解心灵讨论组":
            # 诊断间逻辑
            dynamic_instructions = ""
            if unknown_artist:
                dynamic_instructions += "\n⚠️ 艺术家身份未知，请忽略背景分析，强制执行盲测模式。"
            if unknown_year:
                dynamic_instructions += "\n⚠️ 创作年份未知，请跳过宏观历史分析，仅推测可能的年代感。"

            user_prompt_content = f"""
            【艺术品档案】
            艺术家: {artist_name}
            作品名: {artwork_title if artwork_title else "未知"}
            年份: {artwork_year}
            
            {dynamic_instructions}
            
            请基于 System Instruction 中的角色设定，对这张图片进行深度分析。
            """
            
            final_system_prompt = PROMPT_DIAGNOSTIC

        else:
            # 领读人逻辑
            current_title = artwork_title if artwork_title else "未知作品"
            current_artist = artist_name if artist_name else "未知艺术家"
            current_year = artwork_year if artwork_year else "未知年份"
            
            # 替换占位符
            final_system_prompt = PROMPT_READER.replace("{{Title}}", current_title)
            final_system_prompt = final_system_prompt.replace("{{Artist}}", current_artist)
            final_system_prompt = final_system_prompt.replace("{{Year}}", current_year)
            
            user_prompt_content = "请开始解读。"

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
