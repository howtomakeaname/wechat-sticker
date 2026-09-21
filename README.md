# 微信表情包工作坊 · wechat-sticker

一个把角色参考图制作成微信表情专辑素材的 Agent Skill。支持九宫格表情、少量中文梗图、宣传横幅和透明封面，并为不同生成类别提供独立 reference。

它把系列创作中的经验整理成可复用流程：角色一致性、续作梗与动作去重、中文检查，以及精确尺寸和真实透明度验收。

## 能做什么

| 类别 | 默认输出 | reference |
| --- | --- | --- |
| 纯表情九宫格 | 3×3，一张图九个动作 | [sticker-grid.md](references/sticker-grid.md) |
| 少量中文九宫格 | 默认 3–4 格短文字，其余无字 | [sticker-grid.md](references/sticker-grid.md) |
| 梗图／系列续作 | 按已有文字、动作和场景记录去重 | [memes.md](references/memes.md) |
| 宣传横幅 | 750×400 PNG | [banner.md](references/banner.md) |
| 专辑封面 | 240×240 PNG、透明、无白描边 | [cover.md](references/cover.md) |
| 导出与检查 | 像素尺寸、格式、Alpha、大小；可选单格裁切 | [export-and-qa.md](references/export-and-qa.md) |

尺寸是来自制作案例的可覆盖预设，不是微信官方完整规范。平台要求有更新时，以用户提供的当前提交页面为准。九宫格是合集图，不等于可以直接上传的九个独立表情文件。

## 安装到 Codex

下载仓库 ZIP 并解压，或克隆仓库。在仓库根目录执行以下命令，将整个目录复制成一个名为 `wechat-sticker` 的 skill：

```bash
skill_destination="${CODEX_HOME:-$HOME/.codex}/skills/wechat-sticker"
if [ -e "$skill_destination" ]; then
  printf '目标已存在，请先比较现有版本：%s\n' "$skill_destination"
else
  mkdir -p "$skill_destination"
  cp SKILL.md requirements.txt "$skill_destination/"
  cp -R agents references assets scripts "$skill_destination/"
fi
```

其他支持 `SKILL.md` 的宿主可按自己的技能加载方式使用本目录。可读规范不依赖 Python；运行附带图片处理脚本需 Python 3.9+ 和 Pillow：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

图像生成由宿主提供。仓库不内置 API key，不绑定付费服务，也不调用模型。附带脚本只进行本地检查、尺寸调整和裁切，不负责绘制角色或智能抠图。

## 调用示例

附上自己的角色图后，可以直接说：

> 使用 $wechat-sticker，基于这张角色图做 Q 版九宫格，三个格子带简短中文，其余无字。

> 使用 $wechat-sticker，再整一套可爱的梗，角色保持一致，不要与上一套的文字和动作重复。

> 使用 $wechat-sticker，给这个表情专辑做 750×400 宣传横幅，标题用“今天也要可可爱爱”。

> 使用 $wechat-sticker，做 240×240 透明封面，正面半身，无文字、无白色描边，检查是否超过 500KB。

续作时保留前一轮生成的 `character.md`、`sticker-history.json` 和图片。换会话时一并提供，才能可靠去重。

## 本地图片工具

```bash
# 只读检查，--profile cover 验证尺寸、PNG、实际透明像素和非空内容
.venv/bin/python scripts/image_assets.py check output/cover.png --profile cover

# 精确导出。输入必须已经有实际透明背景；不透明输入会失败，不会“伪造”透明。
.venv/bin/python scripts/image_assets.py export source/cover.png output/cover.png --profile cover

# 横幅默认等比裁切；也可选择等比适配并填充
.venv/bin/python scripts/image_assets.py export source/banner.png output/banner.png --profile banner --fit contain --background '#EAF3FF'

# 按 3×3 数学等分裁切；输入有不等间距时用 --boxes 指定实际边界
.venv/bin/python scripts/image_assets.py split-grid output/grid.png output/tiles
```

工具输出 JSON；验收不通过退出码为 1，参数或文件错误为 2。默认不覆盖已有文件。裁切不等于去背景：圆角卡片、边框、底色和文字都会保留。

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
  export-and-qa.md            文件导出、命令与验收
assets/
  sticker-history.template.json
scripts/image_assets.py      本地图片工具
tests/test_image_assets.py   图片工具行为测试
.github/workflows/check.yml  Python 测试与依赖安装
```

## 开发与发布

```bash
.venv/bin/python -m unittest discover -s tests -v
```

仓库包含中文说明、按类别提示词模板、通用记录模板和本地校验工具。不包含制作案例的原始角色图、私人文件路径、生成成品或密钥。按需添加自己有权发布的示例图片。

许可证为 [MIT](LICENSE)，适用于本仓库的代码、说明和模板；使用者输入或生成的图片不因使用本仓库而自动获得该许可证。这个项目不会替使用者上传或发布微信专辑。
