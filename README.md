# 微信表情包工作坊 · wechat-sticker-skill

一个 Agent Skill：给它一张角色参考图，做出一整套微信表情专辑素材——九宫格表情、少量中文梗图、宣传横幅、透明封面，外加把九宫格拆成九张透明单片的本地工具。

流程来自实际做过几套专辑的经验：角色一致性怎么锚定、续作梗和动作怎么去重、图上中文怎么核对、尺寸和真实透明度怎么验收。每个生成类别有独立的 reference。

## 效果预览

下面这些图来自整理这套流程时的真实案例：同一个角色扩展成不同类型的素材。实际使用时角色由你的参考图决定，画风和细节取决于所用的图像生成工具。

### 九宫格表情

点击图片可查看大图。

| 纯表情 | 少量中文 | 可爱梗续作 |
| --- | --- | --- |
| [![同一银蓝角色的九种无文案 Q 版表情](assets/demos/sticker-grid-expressions.webp)](assets/demos/sticker-grid-expressions.webp) | [![加入收到、好耶、啊、救命等少量中文的九宫格](assets/demos/sticker-grid-captions.webp)](assets/demos/sticker-grid-captions.webp) | [![吃一点、送花、让我康康、贴贴等可爱梗九宫格](assets/demos/sticker-grid-cute-memes.webp)](assets/demos/sticker-grid-cute-memes.webp) |
| 用动作表达情绪 | 四格短文字，其余无字 | 根据已有套组继续设计动作与文案 |

对应流程：[九宫格生成](references/sticker-grid.md) · [梗选择与续作去重](references/memes.md)。续作生成后仍需逐格核对文字和动作，不能仅凭提示词认定已去重。

### 表情合集宣传横幅

750×400 横幅示例，将主角色、表情预览和标题整合成一张宣传图。

![蓝白少女表情包合集宣传横幅，主角色与三个小表情预览](assets/demos/sticker-collection-banner.webp)

对应流程：[宣传横幅](references/banner.md)。以上是便于 GitHub 加载的 WebP 展示图；实际交付仍按用户规格导出 PNG。图片来源与展示尺寸见 [demo 说明](assets/demos/README.md)。

### 拆片与去背景

九宫格是合集图，要当独立表情使用还需拆片并去掉卡片底色。左图是拆出的白底单片，右图是去背景后叠在棋盘格上的效果。

![同一张「好耶」单片：左为拆出的白底图，右为去背景后叠棋盘格](assets/demos/cutout-before-after.webp)

整套九张去背景后的联系表（棋盘格预览）：

![九张透明底表情单片叠在棋盘格上的联系表](assets/demos/cutout-contact-sheet.webp)

对应流程：[拆片去背景与验收](references/cutout.md)。抠图由仓库自带的确定性脚本完成，适用近似均匀的纯色卡片底；复杂背景仍需逐张人工验收。

### 上架效果

同一套素材（横幅、封面、透明单片）上传微信表情商店后的专辑页效果，截图由使用者提供。

![微信表情商店中「SE萌娘」专辑页：横幅、名称与十六个表情缩略图](assets/demos/wechat-album-effect.webp)

## 能做什么

| 类别 | 默认输出 | reference |
| --- | --- | --- |
| 纯表情九宫格 | 3×3，一张图九个动作 | [sticker-grid.md](references/sticker-grid.md) |
| 少量中文九宫格 | 默认 3–4 格短文字，其余无字 | [sticker-grid.md](references/sticker-grid.md) |
| 梗图／系列续作 | 按已有文字、动作和场景记录去重 | [memes.md](references/memes.md) |
| 宣传横幅 | 750×400 PNG | [banner.md](references/banner.md) |
| 专辑封面 | 240×240 PNG、透明、无白描边 | [cover.md](references/cover.md) |
| 九宫格拆透明单片 | 九张去卡片底的透明 PNG + 棋盘格预览 | [cutout.md](references/cutout.md) |
| 导出与检查 | 像素尺寸、格式、Alpha、大小；可选单格裁切 | [export-and-qa.md](references/export-and-qa.md) |

尺寸是来自制作案例的可覆盖预设，不是微信官方完整规范。平台要求有更新时，以用户提供的当前提交页面为准。九宫格是合集图，不等于可以直接上传的九个独立表情文件。

## 安装

本 skill 就是一个含 `SKILL.md` 的目录，任何遵循该约定的 Agent 宿主都能加载。

### 一键安装（推荐）

通过社区通用的 [skills CLI](https://www.npmjs.com/package/skills)，一条命令装到本机一个或多个 Agent：

```bash
# 交互式选择宿主和技能
npx skills add howtomakeaname/wechat-sticker-skill

# 非交互：装到 Codex 和 Claude Code
npx skills add howtomakeaname/wechat-sticker-skill -g -a codex -a claude-code -y
```

安装后重开一个 Agent 会话即可通过 `$wechat-sticker` 调用。

### 手动安装

不同宿主的区别只在技能目录的位置：

| 宿主 | 个人技能目录 |
| --- | --- |
| Codex | `~/.codex/skills`（或 `$CODEX_HOME/skills`） |
| Claude Code | `~/.claude/skills` |
| Kimi Code / Kimi Work | `~/Library/Application Support/kimi-desktop/daimon-share/daimon/skills` |
| 其他宿主 | 按各自文档的技能目录 |

下载仓库 ZIP 并解压，或克隆仓库。在仓库根目录执行以下命令，将整个目录复制成一个名为 `wechat-sticker` 的 skill（默认以 Codex 为例，其他宿主把 `root` 改成上表对应路径即可）：

```bash
root="${CODEX_HOME:-$HOME/.codex}/skills"   # Claude Code 改为 "$HOME/.claude/skills"
skill_destination="$root/wechat-sticker"
if [ -e "$skill_destination" ]; then
  printf '目标已存在，请先比较现有版本：%s\n' "$skill_destination"
else
  mkdir -p "$skill_destination"
  cp SKILL.md requirements.txt "$skill_destination/"
  cp -R agents references assets scripts "$skill_destination/"
fi
```

想跟随仓库更新，也可以用软链接代替复制（`git pull` 即完成升级）：

```bash
ln -s "$(pwd)" "$root/wechat-sticker"
```

Claude Code 还支持项目级安装：把目录放到某个项目的 `.claude/skills/wechat-sticker`，只在该项目中生效。

可读规范不依赖 Python；运行附带图片处理脚本需 Python 3.9+ 和 Pillow：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

图像生成由宿主提供。仓库不内置 API key，不绑定付费服务，也不调用模型。附带脚本只进行本地检查、尺寸调整、裁切和确定性的卡片底去背景（`sticker_cutout.py`，适用近似均匀纯色底），不负责绘制角色，也不做任意场景的通用抠图。

## 调用示例

附上自己的角色图后，可以直接说：

> 使用 $wechat-sticker，基于这张角色图做 Q 版九宫格，三个格子带简短中文，其余无字。

> 使用 $wechat-sticker，再整一套可爱的梗，角色保持一致，不要与上一套的文字和动作重复。

> 使用 $wechat-sticker，给这个表情专辑做 750×400 宣传横幅，标题用“今天也要可可爱爱”。

> 使用 $wechat-sticker，做 240×240 透明封面，正面半身，无文字、无白色描边，检查是否超过 500KB。

续作时保留前一轮生成的 `character.md`、`sticker-history.json` 和图片。换会话时一并提供，才能可靠去重。

## 仓库结构

```text
SKILL.md                     技能入口与按类别路由
agents/openai.yaml            Codex 展示信息
references/
  character-and-history.md   角色锚点与记录方法
  sticker-grid.md            纯表情／少量文字九宫格
  memes.md                   梗选择与续作去重
  banner.md                  750×400 宣传横幅
  cover.md                   240×240 透明封面
  cutout.md                  拆片去背景与验收
  export-and-qa.md            文件导出、命令与验收
assets/
  demos/                    README 效果预览图与说明
  sticker-history.template.json
scripts/image_assets.py      本地图片工具（检查、导出、裁切）
scripts/sticker_cutout.py    卡片底去背景工具
tests/                       两个脚本的行为测试
.github/workflows/check.yml  Python 测试与依赖安装
```

## 开发与发布

```bash
.venv/bin/python -m unittest discover -s tests -v
```

仓库包含中文说明、按类别提示词模板、通用记录模板、本地校验工具，以及经用户选用的生成效果展示图。不包含制作案例的原始角色图、私人文件路径或密钥。示例图集中存放在 `assets/demos/`；日常输入、生成结果和本机交接文件仍由 `.gitignore` 排除。

许可证为 [MIT](LICENSE)，适用于本仓库的代码、说明和模板；使用者输入或生成的图片不因使用本仓库而自动获得该许可证。这个项目不会替使用者上传或发布微信专辑。
