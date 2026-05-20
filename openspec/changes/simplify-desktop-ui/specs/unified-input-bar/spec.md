## ADDED Requirements

### Requirement: 多行文本输入
系统 SHALL 提供一个可输入多行文本的区域，支持 Shift+Enter 换行、Enter 发送消息。

#### Scenario: 单行文本发送
- **WHEN** 用户在输入框中输入 "找关于实习的文档" 后按 Enter
- **THEN** 输入内容作为消息发送给 Agent，输入框清空

#### Scenario: 多行文本输入
- **WHEN** 用户输入第一行文字后按 Shift+Enter，继续输入第二行，然后按 Enter
- **THEN** 两行文本合并为一条消息发送给 Agent

### Requirement: 文件拖拽上传
系统 SHALL 支持用户将文件（PDF、MD 等）拖拽到输入框区域，通过 Electron API 获取文件的真实文件系统路径，并以 chip 形式展示文件名。

#### Scenario: 拖入单个文件
- **WHEN** 用户拖拽 `paper.pdf` 到输入框区域
- **THEN** 输入框上方显示 chip `📄 paper.pdf [✕]`，chip 可以点击 ✕ 移除

#### Scenario: 拖入文件后发送
- **WHEN** 用户拖入文件后直接在输入框中按 Enter（无额外文本）
- **THEN** 消息内容为 "请归档文件 {文件绝对路径}"，发送给 Agent

#### Scenario: 拖入文件并添加备注后发送
- **WHEN** 用户拖入文件后在输入框输入 "这是关于机器学习的论文"，然后按 Enter
- **THEN** 消息内容为 "请归档文件 {文件绝对路径}\n这是关于机器学习的论文"，发送给 Agent

#### Scenario: 移除已拖入的文件
- **WHEN** 用户拖入文件后点击 chip 上的 ✕
- **THEN** chip 消失，下次发送时不携带文件路径

### Requirement: 粘贴支持
系统 SHALL 支持用户在输入框中粘贴文本（Ctrl+V / Cmd+V），粘贴内容直接进入输入区域。

#### Scenario: 粘贴路径
- **WHEN** 用户粘贴 "C:\Users\docs\note.md" 到输入框
- **THEN** 粘贴的文本出现在输入框中，用户可继续编辑或直接发送

#### Scenario: 粘贴 URL
- **WHEN** 用户粘贴 "https://example.com/article" 到输入框
- **THEN** 粘贴的 URL 出现在输入框中，Agent 将在收到后判断是否抓取归档

### Requirement: 发送中禁用输入
系统 SHALL 在等待 Agent 响应期间禁用输入框和发送按钮，防止重复提交。

#### Scenario: 发送后等待响应
- **WHEN** 用户发送消息后，Agent 正在处理
- **THEN** 输入框和发送按钮不可用，显示 loading 状态指示
