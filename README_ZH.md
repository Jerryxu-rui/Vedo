<div align="center">
  <h1 align="center">Vedo: 对话式视频生成平台</h1>

  <div align="center">
  </div>

  <p align="center">
    <img src="https://img.shields.io/badge/🐍Python-3.12-00d9ff?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e">
	<a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/⚡uv-Ready-ff6b6b?style=for-the-badge&logo=python&logoColor=white&labelColor=1a1a2e"></a>
	<img src="https://img.shields.io/badge/License-MIT-4ecdc4?style=for-the-badge&logo=opensourceinitiative&logoColor=white" alt="MIT License">
  </p>

  <p align="center">
    <a href="https://github.com/Jerryxu-rui/Vedo"><img src="https://img.shields.io/github/stars/Jerryxu-rui/Vedo?style=social" alt="GitHub stars"></a>
    <a href="https://github.com/Jerryxu-rui/Vedo/issues"><img src="https://img.shields.io/github/issues/Jerryxu-rui/Vedo" alt="GitHub issues"></a>
    <a href="https://github.com/Jerryxu-rui/Vedo/commits/main"><img src="https://img.shields.io/github/last-commit/Jerryxu-rui/Vedo" alt="GitHub last commit"></a>
  </p>

  <p>
    <a href="readme.md"><img src="https://img.shields.io/badge/English-1a1a2e?style=for-the-badge"></a>
    <a href="README_ZH.md"><img src="https://img.shields.io/badge/中文版-1a1a2e?style=for-the-badge"></a>
  </p>

</div>

---

## 🎬 Vedo 是什么？

**Vedo** 是一个先进的对话式视频生成平台，通过智能多智能体工作流程将想法、剧本和小说转化为完整的视频作品。采用现代化架构，具有基于 WebSocket 的实时通信、A2A（智能体到智能体）协调和响应式 React/TypeScript 前端。

### ✨ 主要特性

- **💬 对话式界面**: 自然语言交互进行视频创作
- **🤖 多智能体编排**: 专门的智能体负责剧本写作、故事板设计、角色设计和视频生成
- **🌐 实时进度跟踪**: 基于 WebSocket 的生成进度实时更新
- **🎨 多种生成模式**:
  - **想法到视频**: 将原始想法转化为完整视频
  - **剧本到视频**: 将剧本转化为视觉叙事
  - **小说到视频**: 将完整小说改编为剧集内容
- **🔗 API 优先设计**: RESTful 和 WebSocket API 便于集成
- **⚡ 现代技术栈**: Python 后端 + FastAPI，React/TypeScript 前端，uv 依赖管理

---

## 🎥 视频演示

Vedo 可以从简单的想法、剧本和小说生成高质量视频。以下是平台创建的一些视频示例：

### 🎬 示例视频

<table>
<tr>
<td align="center" width="33%">
  <strong>视频示例 1</strong><br/>
  <em>想法到视频生成</em><br/>
  <small>猫狗友谊故事</small>
</td>
<td align="center" width="33%">
  <strong>视频示例 2</strong><br/>
  <em>剧本到视频生成</em><br/>
  <small>学校篮球场景</small>
</td>
<td align="center" width="33%">
  <strong>视频示例 3</strong><br/>
  <em>小说到视频改编</em><br/>
  <small>奇幻冒险剧集</small>
</td>
</tr>
<tr>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-ALDTdEFOroreGexJOUocSp0Nn6g">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 1<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-BwcTd4F6rorO9VxSi1wcSPe6nZc">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 2<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-Igw0ddbKEoaA0KxbaO7ctm3qnsb">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 3<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
</tr>
</table>

<table>
<tr>
<td align="center" width="33%">
  <strong>视频示例 4</strong><br/>
  <em>角色一致性</em><br/>
  <small>跨场景保持角色一致</small>
</td>
<td align="center" width="33%">
  <strong>视频示例 5</strong><br/>
  <em>场景过渡</em><br/>
  <small>流畅的摄像机运动</small>
</td>
<td align="center" width="33%">
  <strong>视频示例 6</strong><br/>
  <em>最终合成</em><br/>
  <small>带音频的完整视频</small>
</td>
</tr>
<tr>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-QG6dda8NtoinL8xwkNCcJtusnMg">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 4<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-NxU0dHRqHoXyqRx4MRacgpFhnXd">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 5<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
<td align="center" width="33%">
  <a href="https://oq1k07e2lmv.feishu.cn/wiki/NBiDw5PToi3PPOk4AF9ce36vnjd?fromScene=spaceOverview#share-UZXXdN3bao9WctxvJoZcxWlJn9f">
    <div style="background: #1a1a2e; padding: 20px; border-radius: 10px; color: white; cursor: pointer;">
      🎬 观看视频 6<br/>
      <small>点击在飞书查看</small>
    </div>
  </a>
</td>
</tr>
</table>

*注：视频托管在飞书（中国协作平台）。点击任何视频卡片观看生成的内容。这些展示了 Vedo 在不同生成模式和场景下的能力。*

---

## 🏗️ 架构概述

Vedo 采用模块化、面向服务的架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    前端 (React/TypeScript)                  │
│                    实时 WebSocket 仪表板                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    API 网关 (FastAPI)                       │
│          REST 端点 • WebSocket 连接                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                对话编排器                                    │
│         意图分析 • 工作流管理                               │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌───────────────┬──────────────┬──────────────┬──────────────┐
│               │              │              │              │
▼               ▼              ▼              ▼              ▼
┌──────────────┐┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
│   剧本       ││  故事板     ││   角色      ││   场景      ││   视频      │
│   智能体     ││  智能体     ││   智能体    ││   智能体    ││  生成器     │
└──────────────┘└─────────────┘└─────────────┘└─────────────┘└─────────────┘
```

---

## 🚀 快速开始

### 先决条件

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) 用于 Python 依赖管理
- Node.js 18+（用于前端开发）
- LLM 服务的 API 密钥（OpenAI、Google Gemini 等）

### 安装

1. **克隆仓库**
   ```bash
   git clone https://github.com/Jerryxu-rui/Vedo.git
   cd Vedo
   ```

2. **设置 Python 环境**
   ```bash
   uv sync
   source .venv/bin/activate  # 在 Unix/macOS 上
   # 或在 Windows 上: .venv\Scripts\activate
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 使用您的 API 密钥和配置编辑 .env
   ```

4. **设置前端**（可选，用于开发）
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

5. **运行后端服务器**
   ```bash
   python api_server.py
   ```
   API 服务器将在 `http://localhost:8000` 启动

6. **访问前端**
   在浏览器中打开 `frontend/index.html` 或使用本地服务器提供。

### 配置

编辑 `configs/idea2video.yaml` 或 `configs/script2video.yaml` 以配置您首选的 LLM 提供商和 API 密钥：

```yaml
chat_model:
  init_args:
    model: google/gemini-2.5-flash-lite-preview-09-2025
    model_provider: openai
    api_key: <您的API密钥>
    base_url: https://openrouter.ai/api/v1

image_generator:
  class_path: tools.ImageGeneratorNanobananaGoogleAPI
  init_args:
    api_key: <您的API密钥>

video_generator:
  class_path: tools.VideoGeneratorVeoGoogleAPI
  init_args:
    api_key: <您的API密钥>
```

---

## 📖 使用示例

### 1. 想法到视频
```python
from main_idea2video import generate_video_from_idea

idea = "一只猫和狗成为最好的朋友并一起冒险"
user_requirement = "创建包含3个场景的儿童卡通"
style = "卡通"

result = generate_video_from_idea(idea, user_requirement, style)
```

### 2. 剧本到视频
```python
from main_script2video import generate_video_from_script

script = """
EXT. 公园 - 白天
一只猫和狗在喷泉附近玩耍。
猫: (呼噜声) 这真有趣！
狗: (摇尾巴) 最棒的一天！
"""

user_requirement = "快节奏，动态摄像机角度"
style = "动画"

result = generate_video_from_script(script, user_requirement, style)
```

### 3. Web 界面
启动 API 服务器后，访问 `http://localhost:8000` 使用对话式界面进行视频生成。

---

## 🔧 项目结构

```
Vedo/
├── api_server.py              # 主 FastAPI 服务器
├── api_routes_*.py           # 各种 API 路由模块
├── services/                 # 业务逻辑服务
│   ├── chat_service.py       # 对话聊天服务
│   ├── a2a_agent_coordinator.py  # 智能体协调
│   └── intent_analyzer.py    # 基于 LLM 的意图分析
├── agents/                   # 专门的智能体实现
│   ├── screenwriter.py       # 剧本写作智能体
│   ├── storyboard_artist.py  # 故事板生成
│   └── character_extractor.py # 角色设计
├── frontend/                 # React/TypeScript 前端
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 可重用 UI 组件
│   │   └── hooks/           # 自定义 React 钩子
├── configs/                  # 配置文件
├── tools/                    # 外部 API 集成
└── utils/                    # 实用函数
```

---

## 🤝 贡献

我们欢迎贡献！请参阅我们的[贡献指南](CONTRIBUTING.md)了解详情。

1. Fork 仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m '添加惊人功能'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 使用尖端 AI 模型和 API 构建
- 受生成式 AI 创造潜力启发
- 感谢所有贡献者和开源社区

---

<p align="center">
  <strong>🌟 如果您觉得 Vedo 有用，请在 GitHub 上给我们一个星标！</strong>
</p>

<p align="center">
  <em>用 Vedo 将您的想法转化为视频 🎬</em>
</p>
