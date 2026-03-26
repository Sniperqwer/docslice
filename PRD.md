# PRD：docslice — 文档切片 CLI 工具

## 1. 项目背景与痛点

在 AI 辅助学习的时代，以 NotebookLM 为代表的 RAG（检索增强生成）工具极大地提升了知识吸收效率。NotebookLM 的核心优势在于**精准的引用溯源（Citations）**和**细颗粒度的信源过滤（Source Filtering）**。

然而，在面对官方技术文档（如 Claude Code、Pandas、Scikit-learn 等快速迭代的工程框架）时，现有的知识摄入方式存在明显痛点：

* **单一大文件的灾难**：将整个文档站拼接成单一庞大的 Markdown 喂给大模型，模型构建的"语义树"过于臃肿，引用定位困难，极易产生幻觉。
* **缺乏语义层级**：普通的网页转 Markdown 工具不保留目录层级（父子节点关系）。在没有物理文件夹概念的 NotebookLM 中，丧失层级就等于丧失宏观知识脉络。
* **文档更新频繁**：技术文档迭代极快，全量重新抓取耗时耗力，缺乏增量更新能力。

## 2. 产品愿景

**docslice 要成为"文档站 → LLM 知识源"的标准管道。**

用户面对任何文档网站时，只需一条命令就能获得干净、有序、可裁剪的 Markdown 文件集合——直接喂给 NotebookLM、Claude、GPT 等任何大模型，获得精准的引用和回答。

长期目标：覆盖主流文档框架的开箱即用体验，让"把文档变成 AI 知识源"这件事的成本趋近于零。

## 3. 目标用户

| 用户类型 | 典型场景 | 核心诉求 |
|---------|---------|---------|
| **AI 学习者** | 用 NotebookLM 学习 Claude Code、FastAPI 等框架文档 | 文档切片后保留层级结构，方便引用溯源 |
| **开发者** | 快速迭代中需要持续同步某个库的官方文档 | 增量更新，不重复抓取 |
| **知识管理者** | 将分散的多页文档整理为结构化知识库 | 自动化、可裁剪、批量处理 |

**共同特征**：熟悉命令行操作，对文档质量有要求，不满足于简单的网页复制粘贴。

## 4. 核心工作流

docslice 的使用分三步：**生成蓝图 → 手动裁剪 → 批量抓取**。

### Step 1：生成蓝图

```bash
docslice gen https://docs.anthropic.com/claude/docs
```

工具自动解析目标页面的目录结构，生成 `docslice.yml` 蓝图文件。

### Step 2：手动裁剪（可选但推荐）

用户打开 `docslice.yml`，删除不需要的章节。例如，只保留 "Getting Started" 和 "Core Concepts"，删除 "API Reference" 等冗长章节。

**这是 docslice 的核心设计理念：宁可让用户手动裁剪，也不要自动抓取一堆无用内容污染知识源。**

### Step 3：批量抓取

```bash
docslice fetch --output ./claude_docs
```

工具读取裁剪后的蓝图，逐页抓取正文，转为干净的 Markdown，输出到指定目录。

### 完整流程示意

```
用户输入 URL
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│ docslice gen│ ──→ │ 手动裁剪 yml │ ──→ │docslice fetch│
└─────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                    带编号的 Markdown 文件集合
                                                │
                                                ▼
                                    导入 NotebookLM / 喂给 LLM
```

## 5. 输出物描述

### 文件命名规则

文件名格式：`{层级编号}_{标题slug}.md`

编号规则：按蓝图中的顺序动态生成，父级编号 + 子级编号拼接，保证删减节点后编号始终连续。

### 输出目录示例

```
claude_docs/
├── 00_00_Overview.md
├── 00_01_Quickstart.md
├── 01_Core_Concepts.md
├── 01_00_How_Claude_Code_Works.md
├── 01_01_Permissions.md
└── 02_00_Changelog.md
```

### 文件内容

每个 Markdown 文件包含：
- 干净的正文内容（已剥离导航栏、侧边栏、页脚等噪音）
- 保留原文的标题层级、代码块、表格、列表等格式
- 图片链接保留（V1 不下载图片，V1.5 支持本地化）

### 如何使用输出物

1. **NotebookLM**：将整个输出目录中的 `.md` 文件批量上传为 Sources。文件名中的编号前缀让 NotebookLM 在引用时天然带有章节定位信息。
2. **其他 LLM**：直接将文件内容作为 context 传入，编号前缀帮助模型理解文档的层级结构。

## 6. 核心概念：蓝图文件（`docslice.yml`）

蓝图文件是 docslice 的核心数据结构，它是一份 YAML 格式的目录树描述文件。

### 为什么用 YAML

- YAML 天然适合表达多层级的树状嵌套目录
- 人类可读可编辑——用户可以直接用文本编辑器裁剪章节
- 支持注释，方便用户标记"暂不抓取"的章节

### 蓝图结构概览

```yaml
project_name: "claude_code_docs"
base_url: "https://docs.anthropic.com"
config:
  selector: "article.main-content"   # 正文提取的 CSS 选择器
  delay: 1.5                          # 请求间隔（秒）
toc:
  - title: "Getting Started"
    children:
      - title: "Overview"
        url: "/claude/docs/overview"
      - title: "Quickstart"
        url: "/claude/docs/quickstart"
  - title: "Core Concepts"
    url: "/claude/docs/core-concepts"
    children:
      - title: "How Claude Code Works"
        url: "/claude/docs/how-it-works"
```

蓝图只描述**"抓什么"**（标题、URL、层级关系），不包含实现细节（编号分配、内容哈希等由程序内部处理）。

> 蓝图文件的完整字段定义与技术实现详见 [tech_spec.md](./tech_spec.md)。

## 7. 功能定义与版本规划

### V1：核心流程（gen + fetch）

| 功能 | 说明 |
|------|------|
| `docslice gen <url>` | 解析目标页 TOC 结构，生成 `docslice.yml` 蓝图 |
| `docslice fetch` | 读取蓝图，逐页抓取正文，输出编号 Markdown 文件 |
| `--toc-selector` | 用户指定 TOC 区域的 CSS 选择器 |
| `--preset` | 内置文档框架预设（Docusaurus、MkDocs 等），自动识别 |
| `--output` | 指定输出目录 |
| `--force` | 强制全量重抓（替代 V1 中未实现的 sync） |
| 基础反爬 | 固定 UA、随机 sleep、简单重试 |

### V1.5：增量同步 + 图片

| 功能 | 说明 |
|------|------|
| `docslice sync` | 基于内容哈希的增量同步，仅更新变动页面 |
| `--with-images` | 下载图片到本地 `assets/`，改写 Markdown 中的图片链接 |

### V2：进阶能力

| 功能 | 说明 |
|------|------|
| Metadata / Frontmatter 注入 | 在每个 Markdown 头部注入原始 URL、抓取时间、祖先路径等元数据 |
| 高级反爬 | UA 伪装池、指数退避重试 |

## 8. 设计原则

1. **宁可手动裁剪，也不要错误自动**：docslice 不试图"智能"猜测用户需要哪些章节。它生成完整蓝图，让用户自己决定保留什么。错误的自动化比不自动化更糟糕。

2. **编号即结构**：文件名中的层级编号是 docslice 的核心价值——它在扁平的文件列表中重建了目录树的语义关系，让 LLM 能感知章节之间的层级与顺序。

3. **干净优先**：宁可少抓内容，也不要混入噪音。导航栏、侧边栏、页脚等非正文内容必须被严格剥离。

4. **渐进增强**：V1 只做最核心的 gen + fetch，确保这条路径稳定可靠后，再叠加 sync、图片、元数据等高级功能。不为未来的功能预埋复杂度。
