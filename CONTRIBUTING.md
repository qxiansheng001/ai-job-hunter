# Contributing to AI Job Hunter

感谢你愿意贡献！任何形式的帮助都欢迎。

## 报告 Bug

1. 先搜索 [Issues](https://github.com/qxiansheng001/ai-job-hunter/issues) 确认是否已有人报过
2. 使用 Bug Report 模板创建 Issue
3. 附上错误日志、环境信息（OS、Python 版本、Chrome 版本）

## 提功能请求

使用 Feature Request 模板，清楚描述你想解决的问题和你的方案。

## 提 Pull Request

1. Fork 本仓库
2. 从 `main` 创建分支：`git checkout -b feat/your-feature`
3. 开发你的修改
4. 确保测试通过：

```bash
cd scripts && python -m pytest tests/ -v
```

5. 提交前运行代码格式化：

```bash
pip install pre-commit ruff
pre-commit run --all-files
```

6. PR 到 `main` 分支，描述清楚改了什么、为什么

## 代码风格

- Python 代码使用 [Ruff](https://docs.astral.sh/ruff/) 格式化
- 提交前运行 `pre-commit run --all-files`
- 新功能请附带测试

## 开发环境

```bash
git clone https://github.com/qxiansheng001/ai-job-hunter.git
cd ai-job-hunter
pip install -r requirements.txt
pip install pytest ruff pre-commit
pre-commit install
```

## 项目看板

查看 [Projects](https://github.com/qxiansheng001/ai-job-hunter/projects) 了解当前开发计划和进度。
