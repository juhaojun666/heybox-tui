# heybox-tui

> 小黑盒社区摸鱼终端工具 —— 在命令行里刷帖子，老板以为你在敲代码。

运行后自动打开一个置顶小窗口显示图片，终端里用键盘操作一切，**不需要鼠标**。

## 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.10 或更高版本 |
| 操作系统 | Windows（图片查看器依赖 tkinter，macOS/Linux 也可运行 TUI） |
| 网络 | 需要能访问 `api.xiaoheihe.cn` 和 `imgheybox.maxmc.cn` |

> Python 3.10 以下版本不支持本项目的语法（如 `X \| Y` 类型联合写法）。

检查你的 Python 版本：

```bash
python --version
# 输出类似 Python 3.12.x 即可
```

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/juhaojun666/heybox-tui.git
cd heybox-tui
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖说明：

| 包名 | 用途 |
|------|------|
| textual | 终端界面框架 |
| httpx | 网络请求 |
| rich | 终端富文本渲染 |
| Pillow | 图片处理（查看器必需） |

> 如果 `pip` 安装太慢，可以用国内镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

## 运行

```bash
python app.py
```

启动后：
- 终端出现帖子列表界面
- 右下角自动弹出一个置顶图片查看器窗口

全程用键盘操作，不需要点图片查看器窗口：

| 按键 | 功能 |
|------|------|
| `↑` / `↓` | 上下选择帖子 |
| `Enter` | 查看帖子详情 |
| `1` / `2` | 切换「推荐」/「最新」 |
| `←` / `→` | 切换图片（上一张 / 下一张） |
| `n` / `p` | 下一页 / 上一页 |
| `r` | 刷新 |
| `Esc` | 返回列表 |
| `q` | 退出 |

> 图片查看器也可以用鼠标操作：点击「上一张」「下一张」按钮，或点击「原图」用系统看图软件打开高清大图。

## 登录（可选）

不登录也能用，但只能看到热门帖子。登录后可以看到符合你兴趣的个性化推荐。

### 配置方法

编辑项目目录下的 `config.json`（和 `app.py` 在同一个文件夹）：

```json
{
  "cookie": "在这里粘贴你的 cookie"
}
```

### 如何获取 cookie

1. 用浏览器打开 [小黑盒官网](https://www.xiaoheihe.cn/)，登录你的账号
2. 按 **F12** 打开开发者工具
3. 点击顶部的 **Network**（网络）标签
4. 刷新页面（F5）
5. 在请求列表中点击任意一个 `api.xiaoheihe.cn` 开头的请求
6. 在右侧找到 **Request Headers**（请求标头）
7. 找到 `Cookie:` 那一行，复制它的完整值
8. 粘贴到 `config.json` 的 `cookie` 字段中

示例（值是示意，请复制你自己的）：

```json
{
  "cookie": "heybox_id=123456; pkey=xxxxxx; _ga=GA1.2.xxx..."
}
```

> `config.json` 已加入 `.gitignore`，不会被提交到仓库，不用担心泄露。

## 常见问题

### 启动后看不到图片查看器

检查是否安装了 Pillow：`pip install Pillow`

### 图片加载失败

可能是网络波动，按 `←` `→` 切换到该图片会自动重试。如果持续失败，检查网络是否能访问 `imgheybox.maxmc.cn`。

### 提示「触发验证码」

请求过于频繁，等几分钟后再试。

## 技术栈

- [Textual](https://textual.textualize.io/) — 终端 TUI 框架
- [httpx](https://www.python-httpx.org/) — HTTP 客户端
- [Rich](https://rich.readthedocs.io/) — 终端富文本渲染
- [Pillow](https://python-pillow.org/) — 图片处理
- [tkinter](https://docs.python.org/3/library/tkinter.html) — 图片查看器窗口（Python 自带）

## 致谢

API 签名算法移植自 [xhhBackCrack](https://github.com/luckylca/xhhBackCrack)
