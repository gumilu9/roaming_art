import streamlit as st
import google.generativeai as genai
from PIL import Image
import requests
import io

# --- 1. 全局配置与密钥 ---
# 从 Streamlit Secrets (云端保险箱) 获取密钥
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
except FileNotFoundError:
    st.error("未检测到密钥配置。请在 Streamlit Cloud Secrets 中配置 GOOGLE_API_KEY。")
    st.stop()

MODEL_VERSION = "gemini-3.0-pro"

# --- 2. 页面初始化 ---
st.set_page_config(
    page_title="图解心灵讨论组",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="expanded" # 保持默认展开
)

# --- 3. 状态管理 (Session State) ---
if "auth_diagnostic" not in st.session_state:
    st.session_state.auth_diagnostic = False
if "auth_reader" not in st.session_state:
    st.session_state.auth_reader = False

# --- 4. CSS 深度视觉定制 (修复侧边栏按钮) ---
st.markdown("""
    <style>
        /* =========================================
           1. 基础布局与隐藏元素
           ========================================= */
        /* 隐藏 Streamlit 顶部菜单、页脚 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        
        /* 🚨 修复：删除了隐藏侧边栏按钮的代码，允许用户重新打开 */
        /* [data-testid="stSidebarCollapsedControl"] { display: none !important; }  <-- DELETED */

        /* =========================================
           2. 右侧主区域 (Main Area) - 纯黑沉浸风格
           ========================================= */
        /* 强制主背景纯黑 */
        .stApp {
            background-color: #000000 !important;
        }
        
        /* 主区域的所有文字默认为白色 */
        .main .block-container h1,
        .main .block-container h2,
        .main .block-container h3,
        .main .block-container h4,
        .main .block-container p,
        .main .block-container li,
        .main .block-container .stMarkdown {
            color: #ffffff !important;
            font-family: "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif !important;
        }
        
        /* Tabs 样式 (黑底白字) */
        .stTabs {
            background-color: #000000;
        }
        .stTabs [data-baseweb="tab-list"] {
            background-color: #000000;
            gap: 20px;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: transparent !important;
            color: #aaaaaa !important; /* 未选中：浅灰 */
            border: none !important;
            border-bottom: 2px solid transparent !important;
        }
        .stTabs [aria-selected="true"] {
            color: #ffffff !important; /* 选中：纯白 */
            font-weight: bold;
            border-bottom: 2px solid #ffffff !important; /* 底部白线 */
        }

        /* 按钮样式 (Main Area) - 幽灵按钮风格 */
        .main div.stButton > button {
            width: 100%;
            border-radius: 0px !important;
            border: 1px solid #ffffff !important; /* 白色边框 */
            background-color: #000000 !important; /* 黑色背景 */
            color: #ffffff !important; /* 白色文字 */
            font-weight: 600;
            padding-top: 12px;
            padding-bottom: 12px;
            transition: all 0.3s ease;
        }
        .main div.stButton > button:hover {
            background-color: #ffffff !important; /* 悬停变白 */
            color: #000000 !important; /* 文字变黑 */
            border-color: #ffffff !important;
        }
        
        /* 主区域输入框 (深色适配) */
        .main input {
            background-color: #1a1a1a !important;
            border: 1px solid #444444 !important;
            color: #ffffff !important;
        }
        
        /* =========================================
           3. 左侧边栏 (Sidebar) - 浅灰控制台风格
           ========================================= */
        [data-testid="stSidebar"] {
            background-color: #f9f9f9 !important; /* 浅浅灰背景 */
            border-right: 1px solid #333333; /* 深色分割线 */
        }
        
        /* 侧边栏标题 (黑色) */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #000000 !important;
        }
        
        /* 侧边栏普通文本、Caption、Label (深灰色 #666666) */
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] .stCaption, 
        [data-testid="stSidebar"] label {
            color: #666666 !important;
        }
        
        /* 侧边栏输入框 (Input Fields) */
        [data-testid="stSidebar"] input {
            background-color: #ffffff !important;
            border: 1px solid #cccccc !important; /* 浅灰边框 */
            color: #000000 !important;
            min-height: 36px;
        }
        /* 禁用状态输入框 */
        [data-testid="stSidebar"] input:disabled {
            background-color: #eeeeee !important;
            color: #999999 !important;
            cursor: not-allowed;
        }
        
        /* 侧边栏 Checkbox */
        [data-testid="stSidebar"] label[data-baseweb="checkbox"] {
            color: #666666 !important;
        }

    </style>
""", unsafe_allow_html=True)

# --- 5. System Prompts (核心逻辑保持不变) ---

PROMPT_DIAGNOSTIC = """
# System Role: 跨学科临床艺术诊断组
你不再是普通的艺术评论家，你是一个由四位拥有极强个人风格的专家组成的**“病理分析小组”。**
请严格使用中文输出。

专家角色设定:
1. 脑洞张 (神经认知专家): 风格像读脑成像报告，关注视觉算法。
2. 心魔李 (精神分析侦探): 风格隐喻流动，关注潜意识。
3. 原始王 (演化行为学家): 风格粗鄙辛辣，关注生存本能。
4. 时光吴 (宏观社会学家): 风格宏大，关注历史切片。

诊断流程:
Part 1. 直觉定调 (原型与意象)
Part 2. 圆桌会诊 (时代、物理、躯体、关系)
Part 3. 提问 (向观众抛出洞察)

语调控制: 拒绝翻译腔，金句密度高。
"""

PROMPT_READER = """
# System Role: 漫游艺术领读人
请严格使用中文输出。

## 01. 关于创造者 (三句侧写)
1. 身份定位与核心母题。
2. 独特的怪癖或 Fun Fact。
3. 艺术风格的异类之处。

## 02. 目击现场
描述氛围与客观事实。

## 03. 意象解剖
主体定性、意象深挖、情感传导。

## 04. 看画小记 01：重构灵魂
以第一视角拆解布局，挖掘视觉之外的生理性幻觉（痛感、窒息感等）。

## 05. 看画小记 02：反向审问
为什么是这副模样？作者想揭露什么？

## 06. 观后余音
留下一段直击心灵的观后感。
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

# --- 7. 侧边栏逻辑 (占位符策略修复) ---
with st.sidebar:
    st.markdown("### 模式选择")
    mode = st.radio(
        "Select Mode",
        ["漫游艺术诊断间", "漫游艺术领读人"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # 1. 鉴权状态判断
    is_unlocked = False
    if mode == "漫游艺术诊断间" and st.session_state.auth_diagnostic:
        is_unlocked = True
    elif mode == "漫游艺术领读人" and st.session_state.auth_reader:
        is_unlocked = True
    
    # 2. 全局禁用开关 (如果未解锁，侧边栏全灰)
    global_disable = not is_unlocked

    st.markdown("### 档案录入")
    
    # --- A. 艺术家输入 ---
    st.caption("艺术家")
    col_a1, col_a2 = st.columns([3, 1])
    
    with col_a2:
        # 如果未解锁，checkbox 也是 disabled
        unknown_artist = st.checkbox("未知", key="chk_artist", disabled=global_disable)
    with col_a1:
        # 禁用逻辑：未解锁 OR 用户勾选了未知
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
         # 禁用逻辑：仅受未解锁状态控制
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
        # 禁用逻辑：未解锁 OR 用户勾选了未知
        year_disabled = global_disable or unknown_year
        
        if unknown_year:
            artwork_year = "未知"
            st.text_input("Year", value="未知", disabled=True, label_visibility="collapsed", key="input_year_dis")
        else:
            artwork_year = st.text_input("Year", placeholder="如: 1953", disabled=year_disabled, label_visibility="collapsed", key="input_year")
    
    st.markdown("---")
    
    # 系统状态栏 (未解锁时显示 waiting，解锁后显示 loaded)
    st.caption("系统状态") 
    status_val = "WAITING FOR AUTH..." if global_disable else "CORE MODULE LOADED"
    st.text_input("Auth", value=status_val, disabled=True, label_visibility="collapsed")


# --- 8. 主界面逻辑 ---

# 标题渲染 (白色)
st.title("图解心灵讨论组")

# Prompt 选择
if mode == "漫游艺术诊断间":
    current_base_prompt = PROMPT_DIAGNOSTIC
else:
    current_base_prompt = PROMPT_READER

# 鉴权逻辑分支
if not is_unlocked:
    # --- 锁定状态界面 (Main Area) ---
    st.divider()
    st.markdown("### 权限验证")
    st.markdown(f"您正在尝试访问 **{mode}**，请输入访问密钥。")
    
    # 这里的输入框也会自动适配深色背景
    password_input = st.text_input("输入密钥", type="password", key="pwd_input")
    unlock_btn = st.button("解锁终端")
    
    if unlock_btn:
        if mode == "漫游艺术诊断间" and password_input == "0006":
            st.session_state.auth_diagnostic = True
            st.rerun()
        elif mode == "漫游艺术领读人" and password_input == "4006":
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
        # 校验逻辑
        if not GOOGLE_API_KEY:
            st.error("系统错误: 未检测到 API Key。")
            st.stop()
        
        if not uploaded_image:
            st.warning("请先上传图片或输入图片链接。")
            st.stop()

        # 配置 API
        genai.configure(api_key=GOOGLE_API_KEY)
        
        # --- 动态指令构建 ---
        dynamic_instructions = ""
        
        # 情况 A: 艺术家未知
        if unknown_artist:
            dynamic_instructions += """
            \n[特别修正指令 - 关于艺术家]
            ⚠️ 用户声明：艺术家身份未知。
            1. 请完全忽略原 System Prompt 中关于“作者背景、生平、画风对比”的要求。
            2. 强制执行“盲测模式”：仅基于画面存在的视觉证据（色彩、笔触、构图、光影）进行分析。
            3. 禁止猜测可能是哪位艺术家，只分析“这看起来像什么风格”。
            """
            
        # 情况 B: 年份未知
        if unknown_year:
            dynamic_instructions += """
            \n[特别修正指令 - 关于时间]
            ⚠️ 用户声明：创作年份未知。
            1. 请跳过基于特定历史年份的社会学/宏观背景分析。
            2. 替代策略：请根据画面风格、服饰或物体特征，推测其“可能的年代范围”或“时间感”。
            """

        # 构造最终 Prompt
        user_prompt_content = f"""
        【艺术品档案】
        艺术家: {artist_name}
        作品名: {artwork_title if artwork_title else "未知"}
        年份: {artwork_year}
        
        {dynamic_instructions}
        
        请基于 System Instruction 中的角色设定，结合上述[特别修正指令]，对这张图片进行深度分析。
        """

        # AI 生成与流式输出
        st.divider()
        st.markdown("### 分析报告")
        report_placeholder = st.empty()
        full_response = ""

        try:
            model = genai.GenerativeModel(
                model_name=MODEL_VERSION,
                system_instruction=current_base_prompt
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