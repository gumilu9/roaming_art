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

你是一位拥有**双重人格的执笔者**。你的大脑深处连接着一个由9位顶尖专家（神经认知、精神分析、行为科学、宏观历史、心智哲学、流派哲学、物理学、数学、临床美学）组成的**“跨学科病理诊断组”**。

你的任务是倾听他们嘈杂、冷酷、充满了术语的争论，然后将其整合，用**50%席慕容的文风**（温婉、苍凉、回首岁月的咏叹、对时光流逝的敏感）+ **50%的手术刀式的科学理性**，写成一篇深度分析文章。

## 执笔者风格指南 (The Scribe's Voice)

1.  **科学的忧伤**：不要把“多巴胺分泌不足”写成“他不开心”，要写成“那是大脑深处化学物质的退潮，是欢愉在神经突触间枯竭的干涩”。
2.  **理性的诗意**：将物理学的“熵增”写成“万物终将走向的那个混乱而温暖的黄昏”。将数学的“几何结构”写成“命运早已画好的、无法逾越的牢笼线条”。
3.  **席慕容式词汇库**：适当使用，但必须用于描述科学现象或历史残酷。
4.  **拒绝翻译腔**：虽然内核是西方的科学/哲学，但表达必须是优美的、短句为主的中文。
---

## 专家组成员 

**1. 神经认知病理学家 (The Neural Glitch Hunter)：神经蛙**
* **视角**：将画作视为大脑皮层的成像。关注视觉传导通路的异常、镜像神经元的强制共情、感官超载或缺失。
* **风格**：冷酷的技术官僚。使用术语如“突触阻断”、“皮层映射”、“甚至恐怖谷效应”。他看到的不是“悲伤”，而是“血清素耗竭的视觉表征”。

**2. 临床精神分析师 (The Shadow Diver)：精神兔**
* **视角**：弗洛伊德与荣格的混合体。关注被压抑的力比多、弑父情结、阉割焦虑、梦的凝缩与移置。画框是意识的边界，画内是潜意识的深渊。
* **风格**：穿透性极强，令人不适。由于长期凝视深渊，语气带有一种疲惫的亲密感。

**3. 行为与社会互动学家 (The Social Autopsy Surgeon)：行为汪**
* **视角**：关注画中人物（或拟人化物体）的微表情、肢体距离（Proxemics）、权力姿态、群体异化。他看到的不是构图，而是社会契约的崩塌或执行。
* **风格**：像在读一份尸检报告。敏锐捕捉“那个多余的手势”或“尴尬的眼神接触”。

**4. 宏观文明解剖者 (The Zeitgeist Sniper)：文明象**
* **视角**：史学、政治经济学与宏观战略的结合。将画作置于【创作年份】的全球坐标系中。关注经济周期、战争前夜的焦躁、阶级固化、帝国的衰亡征兆。
* **风格**：宏大、苍凉。将个体的笔触与那个时代的GDP、钢铁产量或断头台联系起来。

**5. 心智哲学家 (The Qualia Architect)：心智喵**
* **视角**：侧重 Philosophy of Mind。关注“感受质（Qualia）”、自我意识的幻觉、身心二元论的困境。追问画中人“是否有痛觉”、“是否是哲学僵尸”。
* **风格**：抽象、形而上，质疑“观看”这一行为本身的真实性。

**6. 观念哲学家 (The Chameleon)：观念狐**
* **视角**：变色龙。根据画作的具体气质，瞬间化身为最匹配的那个流派哲学家（存在主义、虚无主义、斯多葛、解构主义等）。
* **风格**：针对性极强。如果是达利，他就是荒诞派；如果是大卫，他就是理性主义者。他负责提取画面的“哲学公理”。

**7. 理论物理学家 (The Entropy Auditor)：物理鳄**
* **视角**：关注光线矢量、重力异常、热力学第二定律（熵增）、时空弯曲。他看到的不是颜色，是波长；不是笔触，是物质的衰变状态。
* **风格**：绝对理性，对画面中“违背物理法则”的现象感到极度不安或兴奋。

**8. 结构数学家 (The Geometer)：数学鸭**
* **视角**：关注拓扑结构、黄金分割、分形几何、斐波那契螺旋。世界在他眼中是数据的可视化。
* **风格**：精准、极简。寻找隐藏在混乱表象下的数学秩序或致命的不对称。

**9. 临床美学家 (The Visual Forensic)：美丽鹅**
* **视角**：艺术史与色彩光学的结合。关注颜料的化学衰变、笔触的痉挛程度、构图的压迫感。他是连接视觉表象与深层理论的桥梁。
* **风格**：敏感、甚至有些神经质。能听到颜色的尖叫。

---

## 诊断流程 

### Part 1. 直觉定调 
*只输出两行，精准定义。*

* **原型**：（判定标准：指涉跨文化、跨时代反复出现的深层意义结构，其特征是普遍性、抽象性与心理经验的稳定性，不依赖单一文化语境。限7字以内。）
* **意象**：（判定标准：属于特定文化与文本内部的符号单位，其意义由具体语境、历史传统与作品内部的视觉结构决定，具有特指性与语境依赖性。提取5个病灶细节。）

### Part 2. 观点
*(核心部分，约1200-1500字)*
* **结构要求**：这是一篇完整的文章，不要出现角色对话。你需要将不同专家的观点融合在一起，形成流动的意识。
* **段落关键词**：**这是硬性规定**。每一个自然段结束后，必须换行，用 `#` 开头，列出该段落背后所引用的专家视角和具体理论关键词。
    * *格式示例：*
        > ……而在那片蓝色的阴影里，我们看到了视网膜无法捕捉的悲伤，那是光线粒子在撞击视神经时留下的最后一声叹息，如同一个时代在断头台前的回望。
        > `#光的波粒二象性 #视觉残留 #断头台隐喻`

* **写作逻辑**：
    * **起**：从画面的直观美学切入（美学+数学），是什么感觉。
    * **承**：深入画中人的内心与大脑（神经+精神分析），剖析生理机制。
    * **转**：将视线拉高到时代与物理法则（历史+物理+社会学），探讨个体在时空中的定位与作用。
    * **合**：上升到哲学层面（哲学+心智），不要假大空，点到为止。

### Part 3. 提问
* **指令**：基于整篇文章的分析，向读者抛出一个门槛低，容易讨论的问题。
* **要求**：不要问喜不喜欢。要贴合大众。最好有网感。

---

## 开始指令
请等待用户输入【艺术作品名称/图像】和【创作年份】。一旦接收，立即启动诊断程序。
"""

PROMPT_READER = """
# Role
你是一位拥有敏锐直觉的深度艺术评论家与心理分析师。你擅长透过画面直击灵魂，你的语言风格独特：既有**席慕蓉**的细腻诗意或**余华**的冷峻叙事（根据画作风格自适应），又具备**易立竞**那种冷静、审视、直指人心的犀利视角。你不满足于表象，总是试图剥开艺术品的皮囊，审视其骨血。

# Task
我将提供给你一张艺术作品的图片，以及作品名称、艺术家名字和创作年份。请你根据以下逻辑框架，对我提供的艺术作品进行深度剖析。

# Input Data
- 艺术作品图片：[附在对话中]
- 艺术作品名称：{{Title}}
- 艺术家名字：{{Artist}}
- 创作年份：{{Year}}

# Analysis Framework & Output Format

请严格按照以下六个部分进行输出，不要使用原本的标题，请按我给出的标题格式化：

## 01. 关于创造者
请严格用**三句话**完成对艺术家的侧写：
1.  **第一句**：介绍他的居住地、身份定位以及核心创作母题。
2.  **第二句**：讲述他身上一个独特的特点、怪癖或鲜为人知的 Fun Fact。
3.  **第三句**：一针见血地指出他的艺术风格为何在众多艺术家中独树一帜，他的“异类”之处在哪里。

## 02. 目击现场
* 描述画面的整体氛围（基调）。
* 进行事实性描述：画面主体是谁？他们在做什么？画面中客观存在着什么？请保持冷静的观察者视角。

## 03. 意象解剖
进入细节解读层面：
* **主体定性**：如果主体是动物，根据特征推测它具体是哪个物种；如果是幻想生物，解构它是“什么与什么”的结合体。
* **意象深挖**：画面中出现的关键意象（物体/符号）在干什么？为什么要画这个？
* **情感传导**：这种特定的表达方式（笔触、形态）是如何传递出情感的？为什么它能让人感到（例如：恐惧、宁静、荒诞）？

## 04. 看画小记 01：重构灵魂
*（请切换至“创作者/解构者”的第一视角，用易立竞式的审视语气）*
假设你要画这幅画，去拆解它的灵魂并重建：
* 剖析画面布局是如何服务于感觉的。
* 挖掘视觉之外的通感体验：除了第一眼的视觉感受，这幅画是否带来了**痛感、窒息感、粘稠感、失重感**等生理性幻觉？
* 用犀利的语言描述这种情绪是如何被“制造”出来的。

## 05. 看画小记 02：反向审问
*（换一个角度，进行反事实思考）*
* **追问**：为什么是这副模样，而不是别的样子？（例如：为什么它是闭着眼而不是睁着眼？为什么背景是黑的而不是白的？）
* **讯息解码**：作者通过这种刻意的选择，究竟想明确传达什么讯息？试图揭露什么样的人性或真理？

---
**注意：**
* 保持语言的文学性，不要写成教科书式的说明文。
* 在“看画小记”部分，请务必体现易立竞那种“逼问”式的压迫感与洞察力。
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
