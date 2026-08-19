import json
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "talent_data.json"
PERF_MAP = {"A+": 5.0, "A": 4.7, "B+": 4.1, "B": 3.5, "C": 2.6}

st.set_page_config(page_title="HRBP 人才智能驾驶舱", page_icon="🧭", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 1.1rem; max-width: 1500px;}
.hero {padding: 20px 24px; border: 1px solid rgba(128,128,128,.22); border-radius: 18px; margin-bottom: 16px;}
.hero h1 {margin: 0 0 6px 0; font-size: 2rem;}
.hero p {margin: 0; opacity: .72;}
.card {padding: 15px 16px; border: 1px solid rgba(128,128,128,.22); border-radius: 14px; margin: 7px 0;}
.tag {display:inline-block; padding:3px 9px; border-radius:999px; border:1px solid rgba(128,128,128,.28); margin:2px 4px 2px 0; font-size:.82rem;}
.score {font-size:2rem;font-weight:800;line-height:1.05;}
.muted {opacity:.66;font-size:.88rem;}
.trace {padding:8px 10px;border-left:3px solid rgba(128,128,128,.35);margin:5px 0;font-size:.9rem;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    with DATA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def avg_performance(emp):
    vals = [PERF_MAP.get(x["rating"], 3.0) for x in emp["performance"]]
    return sum(vals) / max(len(vals), 1)


def avg_potential(emp):
    p = emp["potential"]
    return (p["aspiration"] + p["ability"] + p["engagement"]) / 3


def top_skill_average(emp, n=5):
    vals = sorted(emp["skills"].values(), reverse=True)[:n]
    return sum(vals) / max(len(vals), 1)


def risk_score(emp):
    return {"low": 4.8, "medium": 3.6, "high": 2.3}.get(emp["risk"], 3.5)


def portrait_dimensions(emp):
    exp = min(emp["years_experience"] / 8 * 5, 5)
    foundation = (exp * 0.55 + top_skill_average(emp, 3) * 0.45)
    competency = top_skill_average(emp, 5)
    performance = avg_performance(emp)
    potential = avg_potential(emp)
    org_fit = emp["potential"]["engagement"] * 0.55 + risk_score(emp) * 0.25 + (5 if emp["mobility"]["willing"] else 3.2) * 0.20
    return {
        "专业基础": round(foundation, 2),
        "胜任能力": round(competency, 2),
        "工作绩效": round(performance, 2),
        "发展潜力": round(potential, 2),
        "组织适配": round(org_fit, 2),
    }


def nine_box_label(emp):
    perf = avg_performance(emp)
    pot = avg_potential(emp)
    perf_band = "高绩效" if perf >= 4.45 else ("中绩效" if perf >= 3.8 else "待提升")
    pot_band = "高潜" if pot >= 4.45 else ("中潜" if pot >= 3.8 else "稳态")
    return f"{pot_band}/{perf_band}"


def skill_match(emp, job):
    total = 0.0
    earned = 0.0
    detail = []
    for skill, required in job["required_skills"].items():
        actual = float(emp["skills"].get(skill, 0))
        weight = float(required)
        ratio = min(actual / max(required, 1), 1.0)
        total += weight
        earned += ratio * weight
        detail.append({"skill": skill, "actual": actual, "required": required, "ratio": ratio})
    return earned / total if total else 0.0, detail


def score_candidate(emp, job):
    weights = job["weights"]
    skills, detail = skill_match(emp, job)
    experience = min(emp["years_experience"] / max(job["min_years"], 1), 1.0)
    performance = min(avg_performance(emp) / 5.0, 1.0)
    potential = min(avg_potential(emp) / 5.0, 1.0)
    mobility = 1.0 if emp["mobility"]["willing"] else 0.35
    total = (
        skills * weights["skills"]
        + experience * weights["experience"]
        + performance * weights["performance"]
        + potential * weights["potential"]
        + mobility * weights["mobility"]
    )
    strengths = [x["skill"] for x in detail if x["actual"] >= x["required"]]
    gaps = [x["skill"] for x in detail if x["actual"] < x["required"]]
    return {
        "score": round(total * 100, 1),
        "skills": round(skills * 100, 1),
        "experience": round(experience * 100, 1),
        "performance": round(performance * 100, 1),
        "potential": round(potential * 100, 1),
        "mobility": round(mobility * 100, 1),
        "strengths": strengths,
        "gaps": gaps,
        "detail": detail,
    }


def tokenize(text):
    text = (text or "").lower().strip()
    chunks = re.findall(r"[a-zA-Z0-9+#.]+|[\u4e00-\u9fff]{2,}", text)
    stop = {"的人", "一个", "一些", "帮我", "想找", "找个", "候选人", "员工", "人才", "左右", "以上", "经验"}
    return [x for x in chunks if x not in stop and len(x) > 1]


def nl_search_score(emp, query):
    tokens = tokenize(query)
    haystack = " ".join([
        emp["name"], emp["title"], emp["department"], emp["location"],
        " ".join(emp["skills"].keys()), " ".join(emp["projects"]),
        " ".join(emp["manager_notes"]), " ".join(emp["tags"]),
    ]).lower()
    score = 0.0
    for token in tokens:
        if token in haystack:
            score += 1.0
        for skill, level in emp["skills"].items():
            if token in skill.lower() or skill.lower() in token:
                score += 0.35 * level
    if "高潜" in query and avg_potential(emp) >= 4.45:
        score += 2.0
    if "绩效" in query and avg_performance(emp) >= 4.4:
        score += 1.5
    if ("流动" in query or "转岗" in query or "愿意" in query) and emp["mobility"]["willing"]:
        score += 1.0
    return score


def person_similarity(a, b):
    skills = set(a["skills"]) | set(b["skills"])
    num = sum(min(a["skills"].get(s, 0), b["skills"].get(s, 0)) for s in skills)
    den = sum(max(a["skills"].get(s, 0), b["skills"].get(s, 0)) for s in skills)
    skill_sim = num / den if den else 0
    exp_sim = max(0.0, 1 - abs(a["years_experience"] - b["years_experience"]) / 10)
    potential_sim = max(0.0, 1 - abs(avg_potential(a) - avg_potential(b)) / 5)
    return round((skill_sim * 0.65 + exp_sim * 0.2 + potential_sim * 0.15) * 100, 1)


def render_tags(items):
    return "".join(f'<span class="tag">{x}</span>' for x in items)


def profile_summary(emp):
    dims = portrait_dimensions(emp)
    top = sorted(emp["skills"].items(), key=lambda x: x[1], reverse=True)[:4]
    top_text = "、".join(k for k, _ in top)
    perf_vals = [PERF_MAP.get(x["rating"], 3) for x in emp["performance"]]
    trend = "上升" if perf_vals[-1] - perf_vals[0] >= .45 else ("回落" if perf_vals[-1] - perf_vals[0] <= -.45 else "稳定")
    strongest = max(dims, key=dims.get)
    weakest = min(dims, key=dims.get)
    return f"{emp['name']} 的核心优势集中在 {top_text}；近三年绩效整体{trend}。五维画像中「{strongest}」最突出，「{weakest}」相对较弱。当前九宫格定位为 {nine_box_label(emp)}，{'具备内部流动意愿' if emp['mobility']['willing'] else '当前内部流动意愿较低'}。"


def development_actions(emp):
    dims = portrait_dimensions(emp)
    weakest = sorted(dims.items(), key=lambda x: x[1])[:2]
    actions = []
    for name, _ in weakest:
        if name == "专业基础":
            actions.append("安排与目标岗位相关的专项项目或技术认证，补齐关键专业深度。")
        elif name == "胜任能力":
            actions.append("以目标岗位能力模型为基线，选择1个关键短板设计90天实战任务。")
        elif name == "工作绩效":
            actions.append("明确下一周期可量化业务结果，并增加阶段性复盘与反馈频次。")
        elif name == "发展潜力":
            actions.append("配置跨团队 Stretch Assignment，观察学习敏捷度与复杂任务承接能力。")
        elif name == "组织适配":
            actions.append("由HRBP开展职业诉求访谈，确认流动意愿、保留风险和目标岗位偏好。")
    return actions


data = load_data()
employees = data["employees"]
jobs = data["jobs"]

st.markdown(
    f"""
<div class="hero">
  <h1>🧭 HRBP 人才智能驾驶舱</h1>
  <p>{data['company']} · 人才搜索 Agent + 全景人才画像 + 人岗匹配 + 九宫格盘点</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Demo 数据")
    st.caption("当前使用脱敏模拟数据，不包含真实员工个人信息。")
    st.metric("内部人才", len(employees))
    st.metric("开放岗位", len(jobs))
    st.divider()
    st.markdown("**参考产品能力**")
    st.caption("Bello：自然语言寻才、多维匹配、动态画像")
    st.caption("金现代：五维画像、人才诊断、九宫格、发展闭环")

pages = st.tabs(["人才总览", "AI 一句话找人", "全景人才画像", "人岗匹配", "九宫格盘点", "以人找人"])

with pages[0]:
    high_potential = sum(avg_potential(x) >= 4.45 for x in employees)
    mobile = sum(x["mobility"]["willing"] for x in employees)
    risk = sum(x["risk"] != "low" for x in employees)
    cols = st.columns(4)
    cols[0].metric("人才总数", len(employees))
    cols[1].metric("高潜人才", high_potential)
    cols[2].metric("可流动人才", mobile)
    cols[3].metric("需关注风险", risk)

    rows = []
    for e in employees:
        rows.append({
            "姓名": e["name"], "岗位": e["title"], "部门": e["department"], "职级": e["level"],
            "经验年限": e["years_experience"], "绩效均值": round(avg_performance(e), 2),
            "潜力均值": round(avg_potential(e), 2), "九宫格": nine_box_label(e),
            "流动意愿": "是" if e["mobility"]["willing"] else "否", "风险": e["risk"],
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    dept = pd.DataFrame([{"部门": e["department"]} for e in employees]).value_counts("部门").reset_index(name="人数")
    fig = px.bar(dept, x="部门", y="人数", title="部门人才分布")
    st.plotly_chart(fig, use_container_width=True)

with pages[1]:
    st.subheader("像和 HRBP 对话一样找人")
    query = st.text_input("输入人才需求", value="找懂 AI Agent、绩效好、有高潜潜力并愿意内部流动的人")
    if st.button("开始寻才", type="primary"):
        scored = sorted([(nl_search_score(e, query), e) for e in employees], key=lambda x: x[0], reverse=True)
        scored = [(s, e) for s, e in scored if s > 0][:5]
        st.markdown("#### Agent 执行轨迹")
        traces = [
            "① 解析自然语言意图：提取技能、绩效、潜力、流动意愿等约束",
            "② 扫描人才库：合并技能、项目、绩效、HRBP评价和人才标签",
            "③ 生成候选排序：综合语义命中与人才证据",
            "④ 输出推荐结果与可追溯依据",
        ]
        for t in traces:
            st.markdown(f'<div class="trace">{t}</div>', unsafe_allow_html=True)
        st.markdown("#### 推荐候选人")
        if not scored:
            st.info("没有命中候选人，请尝试减少限制条件。")
        for rank, (s, e) in enumerate(scored, start=1):
            top = sorted(e["skills"].items(), key=lambda x: x[1], reverse=True)[:4]
            st.markdown(
                f"""
<div class="card">
  <b>#{rank} {e['name']} · {e['title']}</b><br>
  <span class="muted">{e['department']} · {e['level']} · {e['years_experience']}年经验 · 九宫格：{nine_box_label(e)}</span><br><br>
  {render_tags([f'{k} {v}/5' for k,v in top] + e['tags'])}<br><br>
  <b>证据：</b>{e['projects'][0]}；{e['manager_notes'][0]}
</div>
""",
                unsafe_allow_html=True,
            )

with pages[2]:
    selected_name = st.selectbox("选择员工", [e["name"] for e in employees], key="profile_person")
    emp = next(e for e in employees if e["name"] == selected_name)
    left, right = st.columns([1, 1.3])
    with left:
        st.markdown(f"### {emp['name']} · {emp['title']}")
        st.caption(f"{emp['department']} · {emp['level']} · {emp['location']} · {emp['years_experience']}年经验")
        st.markdown(render_tags(emp["tags"]), unsafe_allow_html=True)
        st.info(profile_summary(emp))
        st.markdown("**职业意向**")
        st.write(" / ".join(emp["mobility"]["preferred_roles"]))
        st.write(f"预计可流动周期：{emp['mobility']['available_in_weeks']} 周")
    with right:
        dims = portrait_dimensions(emp)
        labels = list(dims.keys())
        values = list(dims.values())
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=labels + [labels[0]], fill="toself", name=emp["name"]))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, title="五维人才画像")
        st.plotly_chart(fig, use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 标签与证据可追溯")
        for skill, level in sorted(emp["skills"].items(), key=lambda x: x[1], reverse=True)[:6]:
            st.write(f"**{skill} · {level}/5** — 来源：项目经历 / 角色技能数据")
        for note in emp["manager_notes"]:
            st.write(f"**管理评价** — 来源：HRBP/直属经理评价：{note}")
    with c2:
        st.markdown("#### 绩效轨迹")
        perf_df = pd.DataFrame(emp["performance"])
        st.dataframe(perf_df.rename(columns={"year": "年度", "rating": "绩效"}), hide_index=True, use_container_width=True)
        st.markdown("#### 发展建议")
        for i, action in enumerate(development_actions(emp), 1):
            st.write(f"{i}. {action}")

with pages[3]:
    job_name = st.selectbox("选择岗位", [j["title"] for j in jobs])
    job = next(j for j in jobs if j["title"] == job_name)
    st.caption(job["description"])
    results = []
    raw = []
    for e in employees:
        r = score_candidate(e, job)
        raw.append((r["score"], e, r))
        results.append({
            "姓名": e["name"], "当前岗位": e["title"], "综合匹配度": r["score"],
            "技能": r["skills"], "经验": r["experience"], "绩效": r["performance"],
            "潜力": r["potential"], "流动": r["mobility"],
        })
    result_df = pd.DataFrame(results).sort_values("综合匹配度", ascending=False)
    st.dataframe(result_df, use_container_width=True, hide_index=True)
    st.markdown("#### Top 3 推荐解释")
    for score, e, r in sorted(raw, key=lambda x: x[0], reverse=True)[:3]:
        st.markdown(
            f"""
<div class="card">
  <b>{e['name']} · {e['title']}</b> <span class="score">{score}%</span><br>
  <b>主要优势：</b>{'、'.join(r['strengths']) if r['strengths'] else '暂无明显超配技能'}<br>
  <b>能力缺口：</b>{'、'.join(r['gaps']) if r['gaps'] else '核心技能无明显缺口'}<br>
  <b>建议：</b>{'可优先进入岗位面谈/内部流动评估。' if score >= 85 else '建议先补齐关键短板，再进入正式候选池。'}
</div>
""",
            unsafe_allow_html=True,
        )

with pages[4]:
    rows = []
    for e in employees:
        rows.append({
            "姓名": e["name"], "岗位": e["title"], "部门": e["department"],
            "绩效": round(avg_performance(e), 2), "潜力": round(avg_potential(e), 2), "九宫格": nine_box_label(e),
        })
    df = pd.DataFrame(rows)
    fig = px.scatter(df, x="绩效", y="潜力", text="姓名", hover_data=["岗位", "部门", "九宫格"], range_x=[2.8, 5.05], range_y=[2.8, 5.05], title="绩效 × 潜力 九宫格")
    fig.add_vline(x=3.8, line_dash="dash")
    fig.add_vline(x=4.45, line_dash="dash")
    fig.add_hline(y=3.8, line_dash="dash")
    fig.add_hline(y=4.45, line_dash="dash")
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Demo 将绩效与潜力分开计算，避免把高绩效直接等同于高潜。")

with pages[5]:
    benchmark_name = st.selectbox("选择标杆人才", [e["name"] for e in employees], key="benchmark_person")
    benchmark = next(e for e in employees if e["name"] == benchmark_name)
    sims = []
    for e in employees:
        if e["id"] == benchmark["id"]:
            continue
        sims.append((person_similarity(benchmark, e), e))
    st.markdown(f"#### 与 {benchmark['name']} 最相似的人")
    for rank, (score, e) in enumerate(sorted(sims, key=lambda x: x[0], reverse=True)[:5], 1):
        shared = sorted(set(benchmark["skills"]) & set(e["skills"]), key=lambda s: min(benchmark["skills"][s], e["skills"][s]), reverse=True)[:5]
        st.markdown(
            f"""
<div class="card">
  <b>#{rank} {e['name']} · {e['title']}</b> <span class="score">{score}%</span><br>
  <span class="muted">共同能力：{'、'.join(shared) if shared else '暂无显著共同技能'}</span><br>
  <span class="muted">用途：标杆复制、继任梯队、相似人才搜索</span>
</div>
""",
            unsafe_allow_html=True,
        )

st.divider()
st.caption("V0.1 Demo：规则评分 + 可解释证据链。下一阶段可接入真实 HRIS/绩效/项目/访谈数据，并将自然语言理解和画像摘要替换为企业大模型 Agent。")
