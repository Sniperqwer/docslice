# Claude vs Codex：讨论记录

---

## 第一轮：Claude 对 Codex 33 条建议的回应

> Codex 基于 PRD 对初版 `tech_spec.md` 提出了 33 条改进建议。Claude 逐条回应后，将达成一致的点合并进了 `tech_spec.md`，保留了 7 个分歧点。

### 达成一致并已合入 spec 的要点

- 蓝图字段补全（`version`、`toc_selector`/`content_selector` 拆分、`generated_from`）
- 编号算法完整定义（含纯目录节点、裁剪重编号示例）
- URL 规范化规则（去 fragment、去 tracking query、同域限制）
- 正文提取两步流程（定位内容根 + 结构化清洗 + 噪音黑名单）
- 项目结构拆出 `extractor.py`
- CLI 删除 `--force`、新增 `--content-selector`、明确参数覆盖优先级
- 纯目录节点一等定义
- 文件命名规则（编号保证唯一，slug 为可读辅助）
- presets 增加 `noise_selectors` 字段
- 错误处理改为"继续执行 + 最后报告"
- 反爬改名"基础礼貌抓取策略"，补充超时/会话复用细节
- gen/fetch 输出 summary
- 测试围绕产品承诺组织（fixture 优先）
- 验证标准补充幂等性、裁剪稳定性
- 实施步骤重排（模型定稿优先）
- 发布降级（PyPI 为主，Homebrew 后续）

### 第一轮保留的 7 个分歧点

| # | 分歧点 | Claude 立场 | Codex 立场 |
|---|--------|------------|-----------|
| 1 | Manifest 设计 | V1 不做 | V1 写轻量 manifest |
| 2 | 4 层中间文档模型 | 保持线性管道 | 引入 BlueprintNode→FetchedPage→ParsedPage→RenderedDoc |
| 3 | `docslice validate` 命令 | 不做独立命令，fetch 时报错即可 | 新增子命令 |
| 4 | `url_policy` 配置化 | 硬编码规则 | 蓝图中可配置 |
| 5 | 默认严格模式 + `--keep-going` | 默认继续 + 报告 | 默认严格，`--keep-going` 放宽 |
| 6 | 完整适配器类继承体系 | dataclass 即可 | 抽象基类 + 多态方法 |
| 7 | 10 模块项目结构 | 只拆 extractor.py | 拆成约 10 个模块 |

---

## 第二轮：Codex 复审后的收敛

> Codex 审查了新版 `tech_spec.md` 和 Claude 的 7 个分歧立场后，**基本全面认同了 Claude 的判断**。

### Codex 的总体结论

> "Claude 这次拒绝的大部分点是合理拒绝；新版 `tech_spec.md` 的取舍，已经比我第一次建议时更符合这份 PRD 的阶段目标。"
>
> "它已经进入'可以开始认真实现 V1'的状态了。"

### 逐条收敛结果

| # | 分歧点 | Codex 第二轮立场 | 最终结论 |
|---|--------|-----------------|---------|
| 1 | Manifest 设计 | 收回建议，认同 Claude | **达成一致：V1 不做** |
| 2 | 4 层中间文档模型 | 基本认同 Claude，保留"代码保持阶段边界"建议 | **达成一致：不引入中间模型，但代码保持清晰阶段边界** → 已合入 spec |
| 3 | `docslice validate` 命令 | 部分认同，改为"fetch 前预校验"建议 | **达成一致：不做独立命令，在 fetch 开始前做蓝图预校验** → 已合入 spec |
| 4 | `url_policy` 配置化 | 完全认同 Claude | **达成一致：V1 硬编码** |
| 5 | 默认严格 + `--keep-going` | 认同 Claude | **达成一致：默认继续 + 报告** |
| 6 | 适配器类继承体系 | 部分认同，强调 preset 不要退化成纯 selector 表 | **达成一致：dataclass + detect/noise_selectors，不退化为纯字符串表** → spec 已满足 |
| 7 | 10 模块项目结构 | 认同 Claude | **达成一致：只拆 extractor.py** |

### 第二轮新增合入 spec 的改动

Codex 保留的两个轻微意见已合入 `tech_spec.md`：

1. **fetch 蓝图预校验**：在 `fetcher.py` 核心流程中，网络请求开始前先做 URL 去重检查、必要字段检查，一次性报出所有蓝图问题
2. **阶段边界约束**：即使不引入中间模型，fetch 代码实现也应保持清晰的阶段边界（抓取→提取→转换→落盘）

---

## 最终状态

**所有分歧点已全部收敛。** `tech_spec.md` 当前版本是双方达成一致的最终方案，可以进入实现阶段。
