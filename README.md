# TokoKita 电商 AI 客服：学员起始项目

配套课程：《云AI服务整合与深度应用》。运行环境为 **阿里云 ECS + Ubuntu 24.04 LTS 64 位（x86_64）+ Python 3.12**，通过浏览器 Workbench 操作。

这是学员起始代码，保留四处练习：余弦相似度、语义检索、订单查询、工具循环。初次运行单元测试的基线是 `7 failed, 6 passed`，实验 2、3 补完后应为 `13 passed`。店铺页面可先部署，完整客服功能按实验逐步完成。

仓库地址：[Louis-yan/tokokita-agent-starter](https://github.com/Louis-yan/tokokita-agent-starter)。

## 项目与依赖

| 内容 | 文件 / 软件 |
|---|---|
| Web 服务与接口 | `app/main.py`；FastAPI、Uvicorn |
| 顾客店铺和聊天页 | `app/static/shop.html`、`app/static/index.html` |
| 模型调用 | OpenAI 兼容客户端；Model Studio 聊天与 embedding 模型 |
| 知识库 | `data/knowledge/` 中 5 份政策，21 个知识块 |
| 教学订单 | `data/orders.json`，8 张虚构订单 |
| 单元测试 | `tests/test_agent.py`，使用假模型 |
| 对话评测 | `eval/cases.yaml`、`eval/run_eval.py`，22 条用例 |
| 云端配置与运维 | `cloud_support/` |

Python 依赖的确定版本见 `requirements.txt`。实验 5 的 RDS 接入会另外加入 MySQL 驱动，原有业务练习不被替换。

## 在 ECS 获取项目

下面的命令在新建 Ubuntu 24.04 LTS 64 位 ECS 的 root Workbench 终端执行：

```bash
apt-get update
apt-get install -y git curl ca-certificates nano unzip python3.12 python3.12-venv python3-pip nginx
git clone --branch main --single-branch https://github.com/Louis-yan/tokokita-agent-starter.git /opt/tokokita-agent
cd /opt/tokokita-agent
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
```

最后的 `7 failed, 6 passed` 是留空练习的预期起点。后续课继续使用这份工作目录。

## 配置与首次启动

先在 Model Studio 取得同工作空间、同地域的按量付费 API Key 和 OpenAI 兼容 Base URL，按顺序执行以下命令。交互配置命令单独运行，按提示输入地址与隐藏的 Key。

```bash
source /opt/tokokita-agent/cloud_support/session.sh
python cloud_support/configure_env.py
```

配置完成后验证两类模型：

```bash
cloudrun python cloud_support/check_models.py
```

可先在 Workbench 前台启动应用，另开一个 Workbench 会话访问 `http://127.0.0.1:8000/healthz`：

```bash
cloudrun uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

结束前台检查后按 `Ctrl+C`。课程实验 0 提供手动创建 systemd 服务、安装与配置 Nginx 的完整步骤。仓库中的 `bootstrap_service.sh` 保存相同部署配置，供已经理解流程的学员复用。

## 课程进度

| 实验 | 在云端完成的任务 |
|---|---|
| 0 | ECS、Python、模型、前台启动、systemd、Nginx 和基线 |
| 1 | 区分网络、进程、模型与业务 TODO |
| 2 | 实现 `cosine` 与 `EmbeddingRetriever.search` |
| 3 | 实现查单与工具循环，完成 13 项测试 |
| 4 | HTTP 评测与基于失败用例的改进 |
| 5 | Docker 构建运行、RDS 数据接入与持久化 |
| 6 | 日志、故障恢复、费用与收尾盘点 |
| 7 | 独立公网验收、发布回滚、OSS 归档后释放资源 |

## 配套脚本

- `configure_env.py`：在 ECS 隐藏输入模型 Key 或 RDS 密码，保存到 `/etc/tokokita-agent.env`。
- `session.sh`、`run_with_env.py`：恢复应用目录、虚拟环境与配置。
- `envctl.py`：修改实验使用的非敏感开关。
- `check_models.py`：验证聊天与向量模型。
- `enable_rds.py`、`rds_backend.py`、`check_rds.py`：实验 5 的可选 RDS 接入和直接查库。
- `release.sh`、`run_image.sh`、`rollback.sh`：镜像版本、配置快照和恢复。
- `save_report.py`：按阶段保存评测报告，校对目标地址，防止覆盖。

店铺、订单与政策为教学虚构数据。API Key 和数据库密码由教学账号配置，存放在 ECS 的受保护目录。仓库中的项目测试不代表已完成真实模型、RDS 或 OSS 联测。
