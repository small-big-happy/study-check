import streamlit as st
import sqlite3
import base64
import os
import json
from datetime import datetime

DB = "task_record.db"

# ---------------------- 背景设置 ----------------------
BG_CONFIG_FILE = "bg_config.json"
BG_IMAGE_DIR = "bg_images"

def load_bg():
    if os.path.exists(BG_CONFIG_FILE):
        try:
            with open(BG_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"type": "none"}

def save_bg(cfg):
    with open(BG_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False)

def apply_bg():
    bg = load_bg()
    # 隐藏右上角英文 Deploy 按钮
    css = '''
        <style>
        [data-testid="stAppDeployButton"] { display: none !important; }
        </style>
    '''
    if bg.get("type") == "image" and os.path.exists(bg.get("image", "")):
        with open(bg["image"], "rb") as f:
            data = base64.b64encode(f.read()).decode()
        mime = bg.get("mime", "image/jpeg")
        css += f'''
        <style>
        html, body, [data-testid="stAppViewContainer"] {{
            background-image: url("data:{mime};base64,{data}");
            background-size: cover;
            background-attachment: fixed;
            background-position: center;
        }}
        </style>
        '''
    st.markdown(css, unsafe_allow_html=True)

# ---------------------- 数据库 ----------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT,
                  done INTEGER DEFAULT 0,
                  done_time TEXT,
                  create_time TEXT)''')
    conn.commit()
    conn.close()

def add_task(content):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO tasks (content, done, create_time) VALUES (?,0,?)",
              (content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_tasks():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, content, done, done_time FROM tasks ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows

def mark_done(task_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE tasks SET done=1, done_time=? WHERE id=?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), task_id))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def mark_undone(task_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE tasks SET done=0, done_time=NULL WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

init_db()

# ---------------------- 页面 ----------------------
st.set_page_config(page_title="任务打卡工具", layout="wide")

# 上传框重置：上传成功后自动清空，避免重复上传
if st.session_state.get("bg_upload_clear"):
    if "bg_upload" in st.session_state:
        del st.session_state["bg_upload"]
    st.session_state["bg_upload_clear"] = False

# 侧边栏背景设置（改动后立即应用）
with st.sidebar:
    st.subheader("🎨 背景设置")
    bg = load_bg()
    type_labels = ["无背景", "自定义"]
    label_of = {"none": "无背景", "image": "自定义"}
    cur_type = bg.get("type", "none")
    cur_label = label_of.get(cur_type, "无背景")
    idx = type_labels.index(cur_label) if cur_label in type_labels else 0
    bg_type = st.selectbox("背景类型", type_labels, index=idx)

    if bg_type == "无背景":
        if cur_type != "none":
            save_bg({"type": "none"})
    else:
        # ---- 历史背景库 ----
        st.markdown("**🖼️ 用过的背景**")
        os.makedirs(BG_IMAGE_DIR, exist_ok=True)
        hist = []
        if os.path.exists("bg_image.jpg"):  # 兼容旧版保存的图片
            hist.append("bg_image.jpg")
        for fn in sorted(os.listdir(BG_IMAGE_DIR), reverse=True):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                hist.append(os.path.join(BG_IMAGE_DIR, fn))

        if hist:
            cols = st.columns(2)
            cur_img = bg.get("image", "")
            for i, hp in enumerate(hist):
                with cols[i % 2]:
                    st.image(hp, width=110)
                    b1, b2 = st.columns(2)
                    if b1.button("使用", key=f"use_{hp}"):
                        ext = os.path.splitext(hp)[1].lower()
                        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif"}.get(ext, "image/jpeg")
                        save_bg({"type": "image", "image": hp, "mime": mime})
                        st.rerun()
                    if b2.button("🗑️ 删除", key=f"del_{hp}"):
                        if os.path.exists(hp):
                            os.remove(hp)
                        if bg.get("image") == hp:
                            save_bg({"type": "none"})
                        st.rerun()
            if cur_img in hist:
                st.caption(f"✅ 当前背景：{os.path.basename(cur_img)}")
        else:
            st.caption("还没有用过的背景，先上传一张吧")

        # ---- 上传新背景 ----
        st.markdown("**📤 上传新背景**")
        uploaded = st.file_uploader("上传背景图片（png/jpg）", type=["png", "jpg", "jpeg", "gif"], key="bg_upload")
        if uploaded is not None:
            ext = os.path.splitext(uploaded.name)[1].lower()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "gif": "image/gif"}.get(ext, "image/jpeg")
            fn = f"bg_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
            path = os.path.join(BG_IMAGE_DIR, fn)
            with open(path, "wb") as f:
                f.write(uploaded.getbuffer())
            save_bg({"type": "image", "image": path, "mime": mime})
            st.session_state["bg_upload_clear"] = True
            st.success("新背景已保存并应用")
            st.rerun()

apply_bg()

st.title("📋 任务打卡工具")

# 添加任务
st.subheader("➕ 添加新任务")
with st.form("add", clear_on_submit=True):
    content = st.text_input("任务内容", placeholder="例：背50个英语单词")
    submitted = st.form_submit_button("添加任务")
    if submitted and content.strip():
        add_task(content.strip())
        st.success("已添加任务")
        st.rerun()

tasks = get_tasks()
todo = [t for t in tasks if t[2] == 0]
done = [t for t in tasks if t[2] == 1]

# 待完成任务
st.subheader(f"🕐 待完成任务（{len(todo)}）")
if not todo:
    st.info("暂无待办任务，先在上方添加一个吧")
else:
    for idx, (tid, content, flag, done_time) in enumerate(todo, start=1):
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.write(f"{idx}. {content}")
        if c2.button("✅ 完成", key=f"done_{tid}"):
            mark_done(tid)
            st.rerun()
        if c3.button("🗑️ 删除", key=f"tdel_{tid}"):
            delete_task(tid)
            st.rerun()

# 已完成任务
st.subheader(f"🏆 已完成任务（{len(done)}）")
if not done:
    st.info("还没有已完成的任务，加油！")
else:
    for idx, (tid, content, flag, done_time) in enumerate(done, start=1):
        c1, c2, c3 = st.columns([5, 1, 1])
        date_str = ""
        if done_time:
            try:
                dt = datetime.strptime(done_time, "%Y-%m-%d %H:%M:%S")
                date_str = f"（{dt.month}月{dt.day}日完成）"
            except ValueError:
                date_str = ""
        c1.write(f"~~{idx}. {content}~~ {date_str}")
        if c2.button("↩️ 恢复", key=f"undone_{tid}"):
            mark_undone(tid)
            st.rerun()
        if c3.button("🗑️ 删除", key=f"del_{tid}"):
            delete_task(tid)
            st.rerun()

# 导出
st.subheader("📤 导出已完成任务")
start_input = st.text_input("起始编号（可留空，留空则从 1 开始）")
try:
    start_num = int(start_input.strip()) if start_input.strip() else 1
except ValueError:
    start_num = 1
    st.warning("起始编号不是有效数字，已按 1 开始")
if done:
    # 按完成日期分组：日期行在上方，任务行在下方，一起复制
    def get_date_key(d):
        if d[3]:
            try:
                dt = datetime.strptime(d[3], "%Y-%m-%d %H:%M:%S")
                return dt.strftime("%Y-%m-%d"), f"{dt.month}月{dt.day}日"
            except ValueError:
                pass
        return "9999-99-99", "未知日期"

    ordered = sorted(done, key=get_date_key)
    lines = []
    num = start_num
    last_key = None
    for d in ordered:
        key, date_display = get_date_key(d)
        if key != last_key:
            if last_key is not None:
                lines.append("")
            lines.append(date_display)
            last_key = key
        lines.append(f"{num}：{d[1]}")
        num += 1
    text = "\n".join(lines)
    st.code(text, language=None)
    st.info("点上方代码框右上角的复制按钮，或选中后 Ctrl+C 复制")
else:
    st.info("暂无已完成任务可导出")
