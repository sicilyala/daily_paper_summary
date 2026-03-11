# Daily Paper Summary

一个用于论文情报跟踪的 Python 工具，现在同时支持终端模式和浏览器模式：

- 从 arXiv/IEEE/Scopus 检索近期论文
- 基于关键词和领域描述做相关性排序
- 输出 Top-K 论文英文简报到 `newspaper/markdown/MMDD_papers.md`
- 使用 SQLite 缓存去重与历史追踪（默认 `cache/cache.sqlite3`）
- 内置 48h 运行闸门，避免重复生成
- 浏览器页面可直接点击启动任务并展示最新 `newspaper`

## 1. 项目结构

```text
daily_paper_summary/
├── src/                  # 当前生效的 Python 源码与浏览器静态资源
│   └── backend/          # 新增 FastAPI 后端
│   └── frontend/         # 浏览器端静态页面
│   └── discarded/        # 当前版本已停用的代码文件
├── config/               # 运行配置
├── newspaper/            # 生成的 markdown / pdf 简报
└── test/                 # pytest 测试
    └── backend/         # 与 src/backend 对应的后端测试
```

## 2. Linux 部署

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

## 3. 配置 API Key

```bash
# 临时生效（当前终端）
export GLM_API_KEY="<YOUR_GLM_API_KEY>"
export IEEE_API_KEY="<YOUR_IEEE_API_KEY>"
export SCOPUS_API_KEY="<YOUR_SCOPUS_API_KEY>"

# 持久化到 zsh
echo 'export GLM_API_KEY="<YOUR_GLM_API_KEY>"' >> ~/.zshrc
echo 'export IEEE_API_KEY="<YOUR_IEEE_API_KEY>"' >> ~/.zshrc
echo 'export SCOPUS_API_KEY="<YOUR_SCOPUS_API_KEY>"' >> ~/.zshrc
source ~/.zshrc
```

## 4. 终端模式

```bash
cd /path/to/daily_paper_summary
source .venv/bin/activate && python main.py --config config/default_config.json --deleteLastFile
```

## 5. 浏览器模式

```bash
cd /path/to/daily_paper_summary
source .venv/bin/activate && python -m uvicorn backend.web_app:app --host 127.0.0.1 --port 8000

# or run this on remote 
ssh -L 8000:127.0.0.1:8000 weiqihk@hkpc 'cd /home/weiqihk/Opencode/daily_paper_summary && source .venv/bin/activate && python -m uvicorn backend.web_app:app --host 127.0.0.1 --port 8000'
```

Then open the browser and navigate to:

```text
http://127.0.0.1:8000
```

The page includes:

- `开始生成` 按钮：触发一次新的摘要任务
- `清理当天已有输出后重新生成` 选项：对应原来的 `--delete-last-file`
- 最新简报展示区：直接在浏览器查看 `newspaper`

## 6. 输出位置

```bash
# 简报文件
ls -lh newspaper/

# SQLite 缓存
ls -lh cache/cache.sqlite3
```

## 7. 运行测试

```bash
cd /path/to/daily_paper_summary
source .venv/bin/activate && pytest -q
```

## 8. Linux 定时任务（cron，每天 09:00 触发）

程序内部有 48h 闸门，因此每天触发也不会重复写入。

```bash
cd /path/to/daily_paper_summary
(crontab -l 2>/dev/null; echo '0 9 * * * cd /path/to/daily_paper_summary && /bin/bash -lc "source .venv/bin/activate && python main.py --config config/default_config.json >> newspaper/cron.log 2>&1"') | crontab -

# 查看当前 crontab
crontab -l
```
