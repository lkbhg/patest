# 这是一个简易的python爬虫 🎨🖼️

该项目是个人用于学习并行IO而开发的爬虫程序。包含了多进程/线程/协程等多种并行方案。
能够针对某些特定网站通过Session自动获取Cookies,或者利用附加Cookies实现访问。

## 功能 ✨

- **自动获取cookies**：在特定的网站中可以绕过反爬机制，同时可以使用cookies多发的模式，防止封ip。🧹
- **文件名清理**：删除文件名中的非法字符、控制字符和表情符号和长度。
- **页面处理**：将页面中的标题，内容等解析出来，可以通过自定标签的方式选择需要解析的内容，并保存为txt文件。📸
- **同标题处理**：对于同标题的文件，可以实现保留大文件/序列命名。
- **文件夹管理**：自动提取项目的名称，根据文件序列数量，将内容划分到二级子目录中。📂

## 环境要求 🖥️

- Python 3.9+ 🐍
- tqdm 库（用于显示进度条）📊

建议直接通过patest内的环境配置，使用`uv sync`来构建一个新的环境
（与一般的项目不同，这个项目的环境文件被放在了二级目录patest下面）

## 配置项 ⚙️

按需要配置config.json文件


## 许可证 📝

该项目采用 BSL 许可证 - 详情请查看 LICENSE 文件。📜
- Free for research and personal use
- Commercial use requires a commercial license


### 说明

* **贡献**：Kan Liu 🤝
* **联系**：[lkbhg@outlook.com](mailto:lkbhg@outlook.com) 📧