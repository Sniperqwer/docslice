# docslice V1 可执行技术文档

> 产品背景、用户画像与功能定义详见 [PRD.md](./PRD.md)。
> 设计讨论与分歧收敛记录详见 [claude_sug.md](./claude_sug.md) 与 [codex_sug.md](./codex_sug.md)。

**本文档定位**：这是 docslice V1 的权威实现依据。  
任何工程师或 AI agent 实现 V1 时，都应以本文档中的行为定义、接口约束、边界规则和测试标准为准；不要自行扩展 V1 范围，也不要把本文档未声明的行为“智能补全”成产品能力。

**V1 范围约束**：

- CLI 形态，使用 `typer`
- 仅支持静态 HTML 文档站
- 核心链路是 `gen -> 手动裁剪 -> fetch`
- 优先保证输出质量和行为稳定，不追求站点覆盖率

**V1 非目标**：

- `sync` 增量同步
- 图片下载与本地化
- 动态渲染页面支持
- 高级反爬
- Homebrew 分发

**Python 版本**：`>=3.10`

---

## 1. 产品目标与实现原则

V1 只做一件事：把一个文档站切成**干净、有序、可裁剪、适合给 LLM 使用**的 Markdown 文件集合。

实现时必须始终遵守以下原则：

1. **宁可少自动，也不要错误自动**
   - 没有可靠 TOC 就报错，不要乱猜。
   - 没有可靠正文根节点就报错，不要把整页 HTML 粗暴转 Markdown。
2. **编号即结构**
   - 文件名前缀必须稳定表达层级关系。
   - 编号基于蓝图结构，而不是基于抓取成功结果。
3. **干净优先**
   - 宁可漏掉边角内容，也不要混入导航、页脚、页内目录等噪音。
4. **渐进增强**
   - V1 只实现 PRD 已确认的能力，不为 V1.5/V2 预埋复杂状态系统。

---

## 2. CLI 契约

### 2.1 `docslice gen`

```bash
docslice gen <url> [--toc-selector "..."] [--content-selector "..."] [--preset NAME]
```

**输入**：

- 必填：入口 URL
- 可选：
  - `--preset`
  - `--toc-selector`
  - `--content-selector`

**参数优先级**：

1. 用户显式传入参数
2. 命中的 preset
3. 内容提取 fallback 链

**行为**：

1. 请求入口 URL
2. 解析 HTML
3. 决定 TOC / content 提取策略
4. 解析 TOC 树
5. 对 TOC 内 URL 做规范化和去重
6. 生成 `docslice.yml`
7. 输出 summary

**蓝图输出路径**：

- 固定写入当前工作目录下的 `docslice.yml`
- 若文件已存在，直接覆盖

**失败条件**：

- 请求入口页失败
- 未命中 preset，且用户未提供 `--toc-selector`
- `toc_selector` 无匹配
- 匹配到 TOC 容器但提取后无有效节点

**退出码**：

- `0`：成功
- `1`：运行时失败
- `2`：用户输入或蓝图规则错误

### 2.2 `docslice fetch`

```bash
docslice fetch [--output PATH] [--delay FLOAT]
```

**输入**：

- 当前工作目录下的 `docslice.yml`
- 可选：
  - `--output`
  - `--delay`

**默认值**：

- `--output` 默认 `./output`
- `--delay` 默认读取 `docslice.yml` 中 `config.delay`；若缺失则使用 `1.5`

**行为**：

1. 读取并校验 `docslice.yml`
2. 预先计算全部输出文件编号
3. 对每个有 URL 的节点依次抓取
4. 提取并清洗正文
5. 转换成 Markdown
6. 写入输出目录
7. 输出成功/失败 summary

**输出目录规则**：

- 不存在则创建
- 同名文件覆盖
- 不自动删除旧文件
- 文档必须明确提示：用户裁剪蓝图后重新 fetch，目录中可能残留旧文件；若要完全一致结果，应手动清空输出目录

**退出码**：

- `0`：全部成功
- `1`：存在部分失败或运行时失败
- `2`：蓝图结构错误、配置错误、缺少 `docslice.yml`

---

## 3. 蓝图契约（`docslice.yml`）

蓝图是 V1 的核心数据结构，负责描述“抓什么”。

### 3.1 字段定义

```yaml
version: 1
project_name: "claude_code_docs"
base_url: "https://docs.anthropic.com"
generated_from: "https://docs.anthropic.com/claude/docs"
config:
  toc_selector: ".menu__list"
  content_selector: "article"
  delay: 1.5
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

### 3.2 字段约束

- `version`
  - 固定为 `1`
- `project_name`
  - 必填，字符串
- `base_url`
  - 必填，站点根 URL，必须是绝对 URL
- `generated_from`
  - 可选，记录 `gen` 时的入口 URL
- `config.toc_selector`
  - 可选，字符串
- `config.content_selector`
  - 可选，字符串
- `config.delay`
  - 可选，浮点数，默认 `1.5`
- `toc`
  - 必填，非空列表

### 3.3 节点类型

| 类型 | 要求 | 行为 |
|------|------|------|
| 纯目录节点 | `title` 必填，`url` 为空，允许 `children` | 不抓取，不出文件，但参与编号层级 |
| 叶子节点 | `title` 必填，`url` 非空，`children` 可空 | 抓取并出文件 |
| 有 URL 的父节点 | `title` 必填，`url` 非空，`children` 非空 | 自身出文件，子节点也出文件 |

### 3.4 `url` 存储规则

- 蓝图中的 `url` 必须存储为**相对路径**
- 相对于 `base_url`
- `gen` 过程中先做绝对 URL 规范化，再在写回蓝图时转换为相对路径
- 若规范化后 URL 不属于同域，则不得写入蓝图

### 3.5 YAML 写入规则

为避免不同实现生成不一致的蓝图，字段顺序固定为：

1. `version`
2. `project_name`
3. `base_url`
4. `generated_from`
5. `config`
6. `toc`

`config` 内字段顺序固定为：

1. `toc_selector`
2. `content_selector`
3. `delay`

### 3.6 用户可手动修改的边界

允许用户手动修改：

- `project_name`
- `base_url`
- `config.toc_selector`
- `config.content_selector`
- `config.delay`
- `toc` 树中的节点删除、重排、标题修改

允许但不推荐用户手动新增节点。若新增节点，仍必须满足蓝图 schema。

`fetch` 前的预校验必须覆盖：

- 顶层结构是否合法
- `toc` 是否为空
- 节点是否都有 `title`
- `url` 是否是合法相对路径或合法绝对同域 URL
- 同一个规范化 URL 是否重复出现

---

## 4. 编号与文件命名

### 4.1 编号规则

编号在 `fetch` 时动态计算，不写回蓝图。

规则固定如下：

1. DFS 遍历 `toc` 树
2. 按同层出现顺序分配编号
3. 每层编号固定两位零填充：`00` 到 `99`
4. **所有节点都参与编号**
5. 只有有 URL 的节点输出文件
6. 编号基于蓝图结构，不因抓取失败而变化

### 4.2 示例

给定：

```yaml
toc:
  - title: "Getting Started"
    children:
      - title: "Overview"
        url: "/docs/overview"
      - title: "Quickstart"
        url: "/docs/quickstart"
  - title: "Core Concepts"
    url: "/docs/core-concepts"
    children:
      - title: "How It Works"
        url: "/docs/how-it-works"
```

输出文件：

```text
00_00_Overview.md
00_01_Quickstart.md
01_Core_Concepts.md
01_00_How_It_Works.md
```

### 4.3 裁剪后重编号

- 删除同组内某个节点，只影响该组后续同级节点
- 删除整个父组，会导致后续组整体前移
- 抓取失败不触发重编号

### 4.4 文件命名规则

文件名格式：

```text
{编号前缀}_{slugified_title}.md
```

规则固定如下：

- 编号前缀是唯一性来源
- slug 只用于可读性
- slug 使用 `python-slugify`
- `separator="_"`
- 最大长度 `50`
- 空标题或 slugify 后为空时，使用 `untitled`
- 标题来源优先级：
  1. 蓝图节点 `title`
  2. 页面 `h1`
  3. HTML `<title>`
  4. URL path 最后一段

---

## 5. URL 规范化与链接处理

### 5.1 `normalize_url(url, base_url) -> str | None`

固定处理顺序：

1. 空字符串返回 `None`
2. 用 `urljoin(base_url, url)` 转绝对 URL
3. 解析 URL
4. 若跨域，返回 `None`
5. 若是纯锚点链接，返回 `None`
6. 去掉 `fragment`
7. 去掉所有 `utm_` 开头 query 参数，保留其他 query
8. 若 path 不为 `/` 且以 `/` 结尾，去掉 trailing slash
9. 返回规范化后的绝对 URL

### 5.2 TOC URL 去重规则

- 按规范化后的绝对 URL 去重
- 保留第一次出现的位置和标题
- 后续重复项直接丢弃

### 5.3 正文内链接处理规则

- 相对链接转绝对链接
- 站内锚点链接保留
- 图片链接保留远程 URL，不下载
- 非 HTML 资源链接保留原始 URL

---

## 6. Preset 与提取策略

### 6.1 Preset 定义

V1 使用轻量 `Preset` 结构，不引入复杂继承体系。

每个 preset 至少包含：

- `name`
- `detect(soup) -> bool`
- `toc_selector`
- `content_selector`
- `noise_selectors`

### 6.2 内置 preset

V1 内置以下 preset：

- `docusaurus`
- `mkdocs`
- `gitbook`
- `sphinx`
- `vitepress`

### 6.3 策略优先级

#### `gen` 阶段

- 若用户传 `--preset`：直接使用该 preset；找不到则报错
- 否则自动检测 preset
- 若未命中 preset，必须要求用户传 `--toc-selector`
- `content_selector` 优先级：
  1. 用户 `--content-selector`
  2. preset 的 `content_selector`
  3. 内容 fallback 链

#### `fetch` 阶段

- 只使用蓝图中已经落盘的 `toc_selector` / `content_selector`
- 不重新做 preset 检测

这条规则必须严格遵守，以保证 `gen` 和 `fetch` 可复现。

---

## 7. `gen` 行为规范

### 7.1 TOC 提取范围

V1 只支持“标准导航列表”结构：

- `ul > li > a`
- `ol > li > a`
- `li` 中允许存在无链接的分组标题 + 嵌套子列表

V1 不支持以下结构的自动推断：

- 纯 `div + a` 导航树
- 需要 JS 展开后才完整出现的目录
- 难以区分全站导航与页内目录的复杂布局

### 7.2 TOC 容器选择

- 只在 `toc_selector` 命中的容器内提取
- 若 selector 命中多个元素，使用**第一个命中的元素**
- 若命中容器内既有全站 TOC 又有页内锚点目录，只保留经过 URL 规范化后仍有有效页面 URL 的节点；纯锚点链接会被过滤掉

### 7.3 目录节点提取规则

对每个 `<li>`：

- 优先取第一个直接或浅层子元素中的 `<a>`
- 文本作为 `title`
- `href` 规范化后作为 `url`
- 嵌套 `ul` / `ol` 递归处理为 `children`
- 若无 `<a>`，但有纯文本标题且有子列表，则作为纯目录节点

### 7.4 `gen` summary 输出

至少输出：

- 命中的 preset 名称，或 `manual selector`
- TOC 总节点数
- 有 URL 的节点数
- 纯目录节点数
- 过滤掉的外链数
- 过滤掉的重复 URL 数
- 蓝图保存路径

### 7.5 `gen` 失败文案

失败文案必须可执行，不要只写“解析失败”。

示例：

- `TOC selector '.menu__list' matched no elements`
- `No usable TOC nodes found under selector '.sidebar-nav'`
- `No preset detected and --toc-selector was not provided`

---

## 8. `fetch` 行为规范

### 8.1 蓝图预校验

在开始任何网络请求前，必须一次性完成：

- YAML 结构校验
- 字段类型校验
- `toc` 非空校验
- 节点标题校验
- URL 规范化校验
- 重复 URL 检查

若校验失败，立即退出，不开始抓取。

### 8.2 抓取策略

- 使用单个 `httpx.Client`
- 固定 User-Agent
- `follow_redirects=True`
- timeout：
  - connect=`10s`
  - read=`30s`
- 串行抓取
- 仅对 `429`、`503` 重试，最多 `3` 次，间隔 `5s`
- 每次页面请求后执行礼貌 sleep：`delay +/- random(0, 0.5 * delay)`，下限 `0.1s`

### 8.3 失败处理

- 单页失败时继续抓后续页面
- 命令结束输出失败清单
- 若存在失败页，进程退出码为 `1`
- 失败页不影响其他文件编号

### 8.4 source 注释

每个输出 Markdown 文件顶部都插入：

```md
<!-- source: FINAL_URL -->
```

这里的 `FINAL_URL` 指请求完成并处理重定向后的最终 URL。

---

## 9. 正文提取与清洗规范

### 9.1 内容根节点定位

优先级：

1. 蓝图中的 `config.content_selector`
2. `article`
3. `main`
4. `[role="main"]`
5. `.content`
6. `body`

若最终只能命中 `body`，仍允许继续，但必须对噪音清洗更严格。

若完全无法定位任何节点，则报错。

### 9.2 通用噪音清洗

至少删除以下元素：

- `nav`
- `footer`
- `header`
- `.sidebar`
- `.breadcrumb`
- `.breadcrumbs`
- `.pagination`
- `.table-of-contents`
- `.toc`
- `.copy-button`
- `.copy-code-button`
- `.prev-next`
- `.edit-this-page`
- `.edit-link`
- `script`
- `style`
- `iframe`
- `noscript`

再叠加当前 preset 的 `noise_selectors`。

### 9.3 结构保留规则

以下结构必须尽量保留：

- 标题层级
- 段落
- 列表
- 表格
- 代码块
- 图片
- 普通链接

### 9.4 特殊内容处理

- `admonition` / callout：保留文本内容与标题
- 折叠块：若 HTML 中已有正文内容，则保留其文本
- tabs：保留页面默认可见内容；不尝试合并隐藏 tab
- 代码块语言：
  - 优先读取常见 class，如 `language-python`
  - 读不到语言时，仍输出 fenced code block，但不加语言标记
- 表格：
  - 优先转换为 Markdown 表格
  - 若转换器无法稳定表达，允许保留原始 HTML 表格

### 9.5 清洗与转换职责边界

- `extractor.py` 负责内容根定位、DOM 清洗、链接绝对化
- `converter.py` 只负责把清洗后的 HTML 转为 Markdown

---

## 10. Markdown 输出规范

每个输出文件必须满足：

1. 文件名符合编号与 slug 规则
2. 顶部存在 `<!-- source: ... -->`
3. 文内保留页面主内容，不主动插入 frontmatter
4. 链接使用转换后的 URL
5. 图片保留远程 URL

文内标题规则：

- 如果正文根节点中本就包含页面 `h1`，则保留
- 不额外生成一个与文件名重复的 Markdown 一级标题

---

## 11. 数据模型与模块边界

### 11.1 核心模型

至少包含：

- `TocNode`
- `Config`
- `Blueprint`

字段要求：

```python
class TocNode(BaseModel):
    title: str
    url: str | None = None
    children: list["TocNode"] = Field(default_factory=list)


class Config(BaseModel):
    toc_selector: str | None = None
    content_selector: str | None = None
    delay: float = 1.5


class Blueprint(BaseModel):
    version: int = 1
    project_name: str
    base_url: str
    generated_from: str | None = None
    config: Config = Field(default_factory=Config)
    toc: list[TocNode]
```

### 11.2 模块职责

- `cli.py`
  - 定义 `gen` / `fetch` 命令
- `generator.py`
  - 蓝图生成、TOC 去重、summary 输出
- `fetcher.py`
  - 读取蓝图、编号、抓取、失败汇总、落盘
- `parser.py`
  - TOC 提取
- `extractor.py`
  - 正文提取与清洗
- `converter.py`
  - HTML -> Markdown
- `presets.py`
  - preset 定义与检测
- `utils.py`
  - URL 规范化、slugify、HTTP client、礼貌 sleep

---

## 12. 测试与验收标准

### 12.1 单元测试

必须覆盖：

- `Blueprint` / `TocNode` / `Config` 模型构造与非法输入
- URL 规范化
- slugify 边界
- preset 检测
- TOC 提取
- 编号算法
- 正文提取与清洗
- Markdown 转换关键结构

### 12.2 fixture 测试

至少准备以下 fixture 类型：

- 标准嵌套导航
- 含纯目录节点导航
- 含重复 URL 的导航
- 含锚点目录的页面
- 含表格、代码块、admonition 的正文
- 含典型噪音元素的正文

### 12.3 端到端 smoke test

至少验证：

- 一个 Docusaurus 站点
- 一个 MkDocs 或 Sphinx 站点
- 一个依赖用户显式 `--toc-selector` 的站点

smoke test 的定位是人工验证，不作为核心回归依据；核心回归必须依赖本地 fixture。

### 12.4 验收标准

以下条件全部满足，V1 才算完成：

- `gen` 能稳定生成可编辑蓝图
- 用户手动裁剪蓝图后，`fetch` 仍能正确输出
- 文件编号连续且层级语义正确
- 抓取失败不影响其他文件编号
- 输出 Markdown 不含明显导航、页脚、页内 TOC 等噪音
- 代码块、表格、列表、图片链接基本保留
- 出现部分失败时，用户能从 summary 中明确知道缺了哪些页面

---

## 13. 实施建议（非权威行为定义）

本节是开发顺序建议，不是额外产品规范。实现者可以调整代码提交节奏，但不得改变前文定义的行为。

### Phase 1：基础设施

- 建立 `src` layout 和 `pyproject.toml`
- 实现 `models.py`
- 实现 `utils.py`：
  - `normalize_url`
  - `slugify_title`
  - `create_http_client`
  - `polite_sleep`
- 建立模型、URL、命名相关测试

### Phase 2：目录生成能力

- 实现 `Preset` 结构与内置 preset
- 实现 `parser.py`
- 实现 `generator.py`
- 完成 `docslice gen`
- 建立 preset 与 TOC 解析测试

### Phase 3：正文抓取能力

- 实现 `extractor.py`
- 实现 `converter.py`
- 实现 `fetcher.py`
- 完成 `docslice fetch`
- 建立清洗、转换、编号测试

### Phase 4：集成收口

- 补齐 CLI 行为测试
- 跑 fixture 回归
- 跑少量真实站点 smoke test
- 校正文档示例和 README

---

## 14. 实现禁区

为了避免偏离 PRD，以下行为在 V1 中禁止实现：

- 自动下载图片
- 自动同步增量状态
- 自动写入 frontmatter
- 把失败页面从编号体系中移除
- 为动态站点引入浏览器自动化
- 为少数特殊站点引入过度复杂的抽象层

如果实现过程中遇到必须突破这些禁区的情况，应视为技术方案有问题，需要先回到文档层面修订，而不是直接扩功能。
