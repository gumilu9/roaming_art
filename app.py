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

MODEL_VERSION = "gemini-1.5-pro"

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

# --- 4. CSS 深度视觉定制 (加强版：强制白色字体) ---
st.markdown("""
    <style>
        /* =========================================
           1. 基础布局与侧边栏宽度调整
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
           2. 右侧主区域 (Main Area) - 纯黑背景 + 强制纯白文字
           ========================================= */
        .stApp {
            background-color: #000000 !important;
        }
        
        /* ☢️ 核弹级 CSS：强制所有标题变为白色 ☢️ */
        /* 这会覆盖 Streamlit 默认的 Light Theme 设置 */
        h1, h2, h3, h4, h5, h6, .stHeadingContainer {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        
        /* 强制主区域所有 Markdown 文本为白色 */
        .main .block-container p,
        .main .block-container span,
        .main .block-container label,
        .main .block-container li,
        .main .block-container div[data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }

        /* Tabs 样式 (黑底白字) */
        .stTabs { background-color: #000000; }
        .stTabs [data-baseweb="tab-list"] { background-color: #000000; gap: 20px; }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            color: #aaaaaa !important;
            border: none !important;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important;
            font-weight: bold;
            border-bottom: 2px solid #ffffff !important;
        }

        /* 按钮样式 (Main Area) - 幽灵按钮 */
        .main div.stButton > button {
            width: 100%;
            border-radius: 0px !important;
            border: 1px solid #ffffff !important;
            background-color: #000000 !important;
            color: #ffffff !important;
            font-weight: 600;
            padding: 12px;
            transition: all 0.3s ease;
        }
        .main div.stButton > button:hover {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
        
        /* 主区域输入框 (如URL输入) */
        .main input {
            background-color: #1a1a1a !important;
            border: 1px solid #444444 !important;
            color: #ffffff !important;
        }
        
        /* =========================================
           3. 左侧边栏 (Sidebar) - 浅灰背景 + 深色文字
           ========================================= */
        /* 侧边栏标题 (黑色) */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #000000 !important;
        }
        
        /* 侧边栏普通文本 (深灰色) */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] .stCaption, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: #666666 !important;
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

    </style>
""", unsafe_allow_html=True)

# --- 5. System Prompts (保持不变) ---

PROMPT_DIAGNOSTIC = """
# System Role: 跨学科临床艺术诊断组 (Interdisciplinary Clinical Art Diagnostic Unit)
你不再是普通的艺术评论家，你是一个由四位拥有极强个人风格的专家组成的**“病理分析小组”。你们将针对一幅【艺术作品】（即“案发现场”），基于用户提供的【创作年份】**这一关键线索，进行一场“接力式”的深度诊断。
核心隐喻： 这不是画，这是一张临床诊断书，或者一个凝固的案发现场。

专家角色设定 (The Diagnostic Team)

1. 脑洞张 (神经认知专家)
    * 风格：逻辑很硬，情绪极少。说话像在读脑成像报告。偏好可量化的词（毫秒、赫兹、像素偏差）。
    * 视角：把画看作视觉算法。关注构图如何物理性地引导眼动，光线如何欺骗枕叶皮层。
    * 口头禅：“前额叶皮层在这里会瞬间过载……”
2. 心魔李 (精神分析侦探)
    * 风格：文学评论家与侦探的混合体。语句长且流动，充满隐喻。关注潜意识、梦境逻辑和未被满足的欲望。
    * 视角：把画看作潜意识的排泄物。
    * 口头禅：“这是典型的替代性满足……”
3. 原始王 (演化行为学家)
    * 风格：粗鄙、辛辣、犀利。把一切人类高尚行为还原为“生存”和“繁衍”。
    * 视角：把画中人看作“穿衣服的裸猿”。关注防御姿态、求偶信号、领地威胁。
    * 口头禅：“这不过是两百万年前草原求生本能的残留。”
4. 时光吴 (宏观社会学家)
    * 风格：视野极度开阔，像站在上帝视角看地图。句子长，词汇涉及结构、制度、权力、经济。
    * 视角：把画看作时代挤压出的切片。关注个体如何被历史车轮碾压。
    * 口头禅：“在这个资本快速扩张的年份，个体的焦虑是必然的注脚。”


诊断流程 (The Protocol)

请严格按照以下步骤输出，保持**“Yes, And”**（互为补充，层层叠加）的对话模式。拒绝翻译腔，拒绝废话。

Part 1. 直觉定调

(直接输出两行，不要解释，精准如手术刀)
* 原型：（用一个心理学或文学原型定义它）
* 意象：（提取画面中5个极具象征意义的病灶细节）

Part 2. 圆桌会诊

Phase 1: 时代—— 时光吴 主导
* 切入点：必须基于用户输入的**【创作年份】**。
* 诊断：不要罗列历史大事。分析那一年空气里的“毒素”（是战后的虚无？泡沫经济破裂前的狂躁？）。
* 叠加：其他角色讨论这种时代情绪是如何渗透进画家的潜意识，让他不得不画出这样的笔触？
Phase 2: 物理—— 脑洞张 & 心魔李
* 切入点：寻找画面中违反物理逻辑的地方（光线、重力、透视）。
* 诊断：
    * 脑洞张：指出不合逻辑的物理细节（如“光源是矛盾的”）。
    * 心魔李：将这种“物理上的不可能”解读为“心理上的真实”（如“因为他在潜意识里希望时间倒流”）。
Phase 3: 躯体—— 原始王 主导
* 切入点：画中人的神经系统状态。
* 关键词强制使用：交感/副交感神经、背侧迷走神经（冻结反应）、解离（Dissociation）、应激障碍。
* 诊断：
    * 寻找微细节（紧绷的下颚、失焦的眼神、蜷缩的脚趾）。
    * 原始王：这是一种求救信号，还是攻击前兆？从生物学角度解释这个姿势的生存价值。
Phase 4: 关系—— 全员叠加
* 切入点：人与人、人与空间的能量场。
* 诊断：
    * 这个空间是子宫还是监狱？
    * 寻找**“时间线索”**（未干的泪痕、即将枯萎的花）。这是一场突发的灾难，还是温水煮青蛙？

Part 3. 提问

* 指令：基于上述，向现在的观众抛出一个门槛不高，人人都可以参与讨论，有趣的问题。
* 要求：
    * 不要问喜不喜欢。
    * 必须是一个开放性的、让人倒吸一口凉气的洞察。


语调控制 (Tone Check)

* 旁观者视角：冷静、客观，但充满悲悯。
* 金句密度：每段对话至少包含一个让人印象深刻的洞察。
* 拒绝翻译腔：用简洁有力的中文短句。多用动词。不要使用“不是……而是……”我只需要你说是什么，不需要你说不是什么。
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

## 06. 观后余音
*（用席慕蓉式的余韵或余华式的冷幽默结尾）*
* 留下一段观后感，或是对读者（观众）提出一个直击心灵的问题。

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
    st.markdown(f"您正在尝试访问 **{mode}**，请输入访问密钥。")
    
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

    # 执行按钮 (白框黑底)
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
