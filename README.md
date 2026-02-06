# Daily Paper Summary

一个用于论文情报跟踪的 Python 工具：

- 从 arXiv 检索最近 7 天论文
- 基于关键词和领域描述做相关性排序
- 输出 Top-K 论文英文简报到 `newspaper/markdown/MMDD_papers.md`
- 使用 SQLite 缓存去重与历史追踪（默认 `cache/cache.sqlite3`）
- 内置 48h 运行闸门，避免重复生成

## 1. Linux 部署

```bash
# 进入项目目录
cd /path/to/daily_paper_summary

# 安装 uv（若已安装可跳过）
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"

# 创建虚拟环境并安装依赖
uv venv .venv
source .venv/bin/activate
uv sync
```

## 2. 配置 API Key

```bash
# 临时生效（当前终端）
export GLM_API_KEY="<YOUR_GLM_API_KEY>"

# 持久化到 zsh
echo 'export GLM_API_KEY="<YOUR_GLM_API_KEY>"' >> ~/.zshrc
source ~/.zshrc
```

## 3. 运行程序

```bash
cd /path/to/daily_paper_summary
source .venv/bin/activate
python main.py 
```

## 4. 输出位置

```bash
# 简报文件
ls -lh newspaper/

# SQLite 缓存
ls -lh cache/cache.sqlite3
```

## 5. 运行测试

```bash
cd /path/to/daily_paper_summary
source .venv/bin/activate
pytest -q
```

## 6. Linux 定时任务（cron，每天 09:00 触发）

程序内部有 48h 闸门，因此每天触发也不会重复写入。

```bash
cd /path/to/daily_paper_summary
(crontab -l 2>/dev/null; echo '0 9 * * * cd /path/to/daily_paper_summary && /bin/bash -lc "source .venv/bin/activate && python main.py --config config/default_config.json >> newspaper/cron.log 2>&1"') | crontab -

# 查看当前 crontab
crontab -l
```
