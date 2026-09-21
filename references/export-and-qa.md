# 导出与验收

在 skill 根目录使用 `scripts/image_assets.py`。安装 `requirements.txt` 中的 Pillow；在其他目录执行时使用脚本的实际路径。脚本只处理本地文件，不访问网络或生成模型。

## 命令

```bash
# 通用只读检查
python3 scripts/image_assets.py check INPUT.png

# 内置规格：banner=750×400；cover=240×240 且有实际透明像素
python3 scripts/image_assets.py check INPUT.png --profile cover

# 当前平台或用户有新要求时可覆盖
python3 scripts/image_assets.py check INPUT.png --width 300 --height 300 --require-transparent --max-kb 500

# 封面：输入必须已经抠好图，等比缩放到透明画布；默认边距 3px
python3 scripts/image_assets.py export SOURCE.png OUTPUT.png --profile cover --padding 3

# 横幅：默认等比填满裁切；可指定焦点位置，0/0 左上，1/1 右下
python3 scripts/image_assets.py export SOURCE.png OUTPUT.png --profile banner --anchor-x 0.5 --anchor-y 0.5

# 保留完整横幅，背景填充是明确的布局选择
python3 scripts/image_assets.py export SOURCE.png OUTPUT.png --profile banner --fit contain --background '#EAF3FF'

# 精确数学等分，余数像素均分到每列；不会去背景或去白边
python3 scripts/image_assets.py split-grid SHEET.png output/tiles

# 非等分版式：显式提供九个 [left, top, right, bottom] 像素框
python3 scripts/image_assets.py split-grid SHEET.png output/tiles --boxes crop-boxes.json
```

要把裁出的单格再去除卡片底、得到透明 PNG，继续阅读 [拆片与去背景](cutout.md)。

`crop-boxes.json` 是九个坐标框组成的数组；左上包含、右下不包含。按从左到右、从上到下填写。边框、格间空隙和文字位置要以真实成图决定，不能默认模型一定生成了完美数学网格。

`--width` 和 `--height` 必须一起提供。`export` 无 profile 时需要明确尺寸。`--force` 才能覆盖既有输出；即使用它也不能把输入原图作为输出路径。不要对不透明输入用“添加 Alpha 通道”代替抠图。

## 输出解释

脚本输出 JSON，包含尺寸、格式、文件大小、透明/半透明/不透明像素数、Alpha 内容边界、错误和提醒。

- 退出码 0：文件属性验收通过；仍可能有人工检查项或超大小提醒。
- 退出码 1：文件属性不满足要求，例如封面尺寸错误、没有透明像素、图像全透明。
- 退出码 2：参数、输入文件、坐标或输出路径出错。
- `has_alpha_channel` 只代表存在通道；`has_transparency` 代表确实有非完全不透明的像素。
- 透明封面还要求存在完全透明像素和可见内容。仅有全图统一半透明不是合格抠图。
- `--max-kb` 用 1000 bytes/KB 计算，超出只给提醒。240×240 PNG 通常不大，但仍检查实际文件。

脚本不声称能判断文字是否正确、是否有白色描边、角色是否一致、主体是否被错误抠掉或棋盘格是否残留。Alpha 统计是必要检查，不能替代视觉检查。

## 交付前查看

| 类别 | 文件检查 | 视觉检查 |
| --- | --- | --- |
| 九宫格 | PNG、正方形（如用户有指定尺寸再校验） | 九格、中文准确、无跨格、动作不重复 |
| 横幅 | 精确 750×400 或指定尺寸 | 标题可读，脸与手未被裁掉 |
| 封面 | 精确 240×240、PNG、透明非空、文件大小 | 正面半身/全身、无白描边、少留白、无装饰文字 |

封面最好在浅色和深色预览背景上检查边缘，但这些背景只用于预览，不写入交付 PNG。用户仅要求导出既有图时，不重新设计角色。

保存最终提示词；历史记录引用最终输出，失败草稿不当作已完成。交付文件链接和简短说明即可，不把内部排错过程变成冗长的用户报告。
