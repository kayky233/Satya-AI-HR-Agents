# HRBP 人才智能驾驶舱 Demo

这是一个可直接运行的内部人才画像与人才匹配 Demo，用于快速演示：

- 人才总览
- AI 一句话找人（V0.1 为本地可解释规则检索）
- 五维全景人才画像
- 标签与证据来源追溯
- 人岗匹配与候选人排序
- 绩效 × 潜力九宫格盘点
- 以人找人 / 标杆人才相似搜索
- 基于画像短板的发展建议

> 当前全部数据均为模拟数据，不包含真实员工个人信息。

## 1. 快速启动

```bash
cd demo/talent-intelligence
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 Streamlit 输出的本地地址即可。

## 2. Demo 建议演示路径

### 场景 A：一句话找人

输入：

```text
找懂 AI Agent、绩效好、有高潜潜力并愿意内部流动的人
```

页面会展示 Agent 执行轨迹、候选人排序以及项目/评价证据。

### 场景 B：全景人才画像

选择员工后展示：

- 专业基础
- 胜任能力
- 工作绩效
- 发展潜力
- 组织适配

同时展示技能标签、绩效轨迹、HRBP/经理评价来源和发展建议。

### 场景 C：以岗找人

选择 `AI Agent 技术负责人`、`AI 产品负责人`、`HR 数字化负责人` 等岗位，系统根据：

- 核心技能
- 工作经验
- 历史绩效
- 人才潜力
- 内部流动意愿

进行可解释加权排序，并输出优势、缺口和推荐建议。

### 场景 D：九宫格人才盘点

绩效和潜力分轴展示，避免简单把“高绩效”等同于“高潜”。

### 场景 E：以人找人

选择一个内部标杆人才，系统基于技能结构、经验和潜力寻找相似人才，可用于继任梯队、标杆复制和跨部门调配。

## 3. V0.1 架构

```text
模拟 HR 数据
  ├─ 员工基础信息
  ├─ 技能/项目经历
  ├─ 绩效记录
  ├─ 潜力评估
  ├─ HRBP/经理评价
  └─ 流动意愿
        │
        ▼
Talent Intelligence Engine
  ├─ 五维画像
  ├─ 自然语言规则检索
  ├─ 人岗匹配评分
  ├─ 人才相似度
  ├─ 九宫格定位
  └─ 发展建议
        │
        ▼
Streamlit HRBP 驾驶舱
```

## 4. 与 Satya-AI-HR Agents 的结合方式

当前 Demo 负责“数据、计算、检索和可视化”，Satya-AI-HR Agents 继续作为 HR 专业判断层。

建议下一阶段接入以下 skill：

- `05-performance-and-talent-management/potential-assessment.md`
- `05-performance-and-talent-management/nine-box-calibration.md`
- `05-performance-and-talent-management/succession-profile.md`
- `05-performance-and-talent-management/idp-builder.md`
- `05-performance-and-talent-management/internal-mobility-and-career-paths.md`
- `09-people-analytics-and-reporting/*`

最终形成：

```text
用户问题
  → HR Command Center
  → Talent Intelligence Tool
  → 查询/匹配/画像结果
  → Satya Talent Skill 做专业解释
  → HRBP 决策建议
```

## 5. 下一阶段建议

V0.2 优先级：

1. 接入 OpenAI-compatible / 企业大模型 API，将规则式“一句话找人”升级为真正的 Agent 意图解析。
2. 支持上传 Excel/CSV 员工数据和岗位 JD。
3. 将项目总结、绩效评语、访谈记录通过 LLM 自动抽取为带证据来源的标签。
4. 增加岗位画像配置器和权重配置器。
5. 增加人才对比页面和继任梯队页面。
6. 接入真实 HRIS / 绩效 / 招聘系统，并增加字段级权限与审计日志。

## 6. Demo 定位

这个版本不是完整 HRIS，也不是用于直接替代人工人才决策的自动化评分系统。它的目标是快速证明三个核心价值：

1. 分散的人才数据可以被统一组织成人才资产。
2. HRBP 可以通过自然语言快速找人、看人、比人。
3. AI/规则结果必须能够回到绩效、项目、评价等证据，而不是只给一个不可解释的分数。
