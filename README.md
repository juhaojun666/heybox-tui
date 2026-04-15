# heybox-tui

小黑盒社区摸鱼终端工具，在命令行中浏览小黑盒帖子。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
python app.py
```

## 快捷键

| 按键 | 功能 |
|------|------|
| `1` / `2` | 切换 推荐 / 最新 |
| `n` / `p` | 下一页 / 上一页 |
| `Enter` | 查看帖子详情 |
| `Esc` | 返回列表 |
| `r` | 刷新 |
| `q` | 退出 |

## 技术栈

- [Textual](https://textual.textualize.io/) - 终端 TUI 框架
- [httpx](https://www.python-httpx.org/) - HTTP 客户端
- [Rich](https://rich.readthedocs.io/) - 终端富文本渲染

## 致谢

API 签名算法移植自 [xhhBackCrack](https://github.com/luckylca/xhhBackCrack)
