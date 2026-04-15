# heybox-tui

小黑盒社区摸鱼终端工具，在命令行中浏览小黑盒帖子。

## 安装

```bash
pip install -r requirements.txt
```

## 运行

```bash
# 启动 TUI
python app.py

# 另开一个终端，启动图片查看器（可选）
python viewer.py
```

TUI 和图片查看器联动：在 TUI 中切换帖子时，图片查看器会自动显示对应图片。

> 图片查看器支持 `←` `→` 键切换图片，按 `Esc` 关闭。建议安装 Pillow 以获得更好的图片显示：`pip install Pillow`

## 登录配置（可选）

登录后可获得个性化推荐帖子。编辑配置文件 `~/.heybox-tui/config.json`：

```json
{
  "heybox_id": "你的小黑盒用户ID",
  "pkey": "你的pkey"
}
```

### 获取 heybox_id 和 pkey

1. 在浏览器中打开 [小黑盒](https://www.xiaoheihe.cn/) 并登录
2. 按 F12 打开开发者工具，切换到 Network（网络）标签
3. 刷新页面，找到任意请求 `api.xiaoheihe.cn` 的请求
4. 在请求参数中复制 `heybox_id` 和 `pkey` 的值

> 不配置也能用，只是看不到个性化推荐内容。

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
