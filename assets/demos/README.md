# 效果展示图

这些示例来自创建本 skill 之前、用于提炼其流程的同一角色表情包制作案例，经用户要求加入仓库展示。它们不是对当前仓库完成一轮自动端到端测试的证明，也不表示每次调用都会得到相同结果。

| 文件 | 展示内容 | 展示尺寸 |
| --- | --- | --- |
| [sticker-grid-expressions.webp](sticker-grid-expressions.webp) | 纯表情九宫格 | 840×840 |
| [sticker-grid-captions.webp](sticker-grid-captions.webp) | 少量中文九宫格 | 840×840 |
| [sticker-grid-cute-memes.webp](sticker-grid-cute-memes.webp) | 可爱梗九宫格续作 | 840×840 |
| [sticker-collection-banner.webp](sticker-collection-banner.webp) | 表情合集宣传横幅 | 750×400 |
| [cutout-before-after.webp](cutout-before-after.webp) | 拆片去背景前后对比（右图叠棋盘格） | 904×452 |
| [cutout-contact-sheet.webp](cutout-contact-sheet.webp) | 九宫格拆成的九张透明单片（棋盘格预览） | 840×846 |
| [wechat-album-effect.webp](wechat-album-effect.webp) | 素材上传微信表情商店后的专辑页截图 | 400×702 |

三套九宫格均从原始 1254×1254 PNG 等比缩小；横幅保持 750×400。展示图采用 WebP 编码以减少 README 加载量，插画内容未重新生成。制作流程的正式交付格式仍以用户要求为准。

这里展示的是带底色的合集与横幅，不是透明单片或透明封面的验收样本。九宫格拆片、去背景后需要另行验证真实 Alpha、文字和轮廓完整性。

去背景对比图和联系表由 `scripts/sticker_cutout.py` 实际产出，棋盘格底仅用于展示透明区域；微信专辑页截图为用户提供，用于说明同一套素材上架后的效果，不代表本仓库会代为上传。

本仓库的 MIT 许可证适用于代码、说明和模板，不自动扩展至角色设计和示例图片。示例图片用于说明制作效果。
