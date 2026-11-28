# 文档索引

> 版本：v1.0
> 本目录存放 FireRedASR2S POC 的设计、实现、数据、部署与演化文档。

---

## 1. 文档地图

| 文档 | 内容 | 适合谁 |
| --- | --- | --- |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 正式方案、三语选型、状态机、参数、质量目标 | 架构/决策 |
| [`POC.md`](POC.md) | 当前 POC 范围、接口、配置、实测与运行方式 | 开发/验收 |
| [`EVOLUTION.md`](EVOLUTION.md) | 从第一版 POC 到当前阶段的技术演化与经验 | 学习/复盘 |
| [`DATA.md`](DATA.md) | 个人听写/会议全文的数据采集、标注、划分与校验规范 | 数据/评测 |
| [`RECORDER.md`](RECORDER.md) | 桌面录音器协议、跨机器部署、Windows 打包 | 前端/使用 |
| [`DOCKER.md`](DOCKER.md) | CPU/GPU 后端镜像、运行、端口与模型缓存 | 部署/运维 |

---

## 2. 推荐阅读顺序

### 第一次了解项目

1. `ARCHITECTURE.md`
2. `POC.md`
3. `EVOLUTION.md`

### 要改代码

1. `POC.md`
2. `DOCKER.md`（如果涉及后端镜像）
3. `RECORDER.md`（如果涉及前端）

### 要做数据/评测

1. `DATA.md`
2. `POC.md` 的评测部分
3. `EVOLUTION.md` 中的指标与域偏移经验

### 要部署

1. `DOCKER.md`
2. `POC.md` 的启动/健康检查
3. `RECORDER.md` 的连接地址

---

## 3. 文档约定

- 文档使用中文 Markdown。
- 架构与流程优先使用 Mermaid。
- 术语首次出现时用括号解释。
- 不写参考项目；过程/历史统一记录在仓库根目录 `progress.md`。
- 修改文档时同步更新版本号，不维护 revision log。
