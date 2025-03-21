rss_ai_mailer/
├── main.py                 # 启动入口，运行 GUI
├── gui/                    # GUI 相关代码
│   ├── __init__.py
│   ├── main_window.py      # 主窗口
│   ├── settings_window.py  # 配置窗口
│   ├── tray_icon.py        # 托盘管理
├── core/                   # 核心业务逻辑
│   ├── __init__.py
│   ├── rss_parser.py       # 解析 RSS 订阅源
│   ├── email_sender.py     # 发送邮件
│   ├── scheduler.py        # 任务调度
│   ├── config_manager.py   # 读取和存储用户配置
├── ai_processor/           # AI 处理逻辑（独立包）
│   ├── __init__.py
│   ├── ranker.py           # 新闻排序
│   ├── summarizer.py       # 生成摘要
│   ├── ai_utils.py         # AI 处理工具（连接 GPT API / Ollama）
├── data/                   # 数据存储
│   ├── config.json         # 配置文件
│   ├── rss_feeds.db        # SQLite 数据库（存储 RSS 订阅信息）
├── resources/              # 资源文件
│   ├── icons/              # 托盘图标
│   ├── styles.qss          # 界面样式
└── requirements.txt        # 依赖列表