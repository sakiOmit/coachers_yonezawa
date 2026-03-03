---
name: plugin-scaffold
description: "Claude Code プラグインの雛形ディレクトリ構造を自動生成する。新しいプラグインを作成したい時、プラグイン開発を始める時に使用。"
disable-model-invocation: false
allowed-tools:
  - Read
  - Write
  - Bash
context: fork
agent: general-purpose
---

# Plugin Scaffold Skill

Claude Code プラグインの雛形を自動生成するスキル。

## 使用方法

```
/plugin-scaffold <plugin-name>
```

## 引数

- `$ARGUMENTS` または `$1`: プラグイン名（kebab-case推奨、例: `my-awesome-plugin`）

## 生成されるディレクトリ構造

```
<plugin-name>/
├── .claude-plugin/
│   └── plugin.json       # プラグインマニフェスト（必須）
├── commands/             # スラッシュコマンド（Markdownファイル）
│   └── hello.md          # サンプルコマンド
├── agents/               # サブエージェント定義
│   └── .gitkeep
├── skills/               # エージェントスキル（SKILL.md形式）
│   └── .gitkeep
├── hooks/                # イベントフック
│   └── hooks.json        # フック設定ファイル
└── README.md             # プラグインドキュメント
```

## 実行手順

### Step 1: プラグイン名の取得と検証

1. `$ARGUMENTS` からプラグイン名を取得
2. 名前が空の場合、ユーザーに入力を求める
3. kebab-case形式に正規化（スペース→ハイフン、小文字化）

### Step 2: ディレクトリ構造の作成

以下のコマンドを実行:

```bash
PLUGIN_NAME="$1"
mkdir -p "${PLUGIN_NAME}/.claude-plugin"
mkdir -p "${PLUGIN_NAME}/commands"
mkdir -p "${PLUGIN_NAME}/agents"
mkdir -p "${PLUGIN_NAME}/skills"
mkdir -p "${PLUGIN_NAME}/hooks"
```

### Step 3: plugin.json の生成

`.claude-plugin/plugin.json` を以下の内容で作成:

```json
{
  "name": "<plugin-name>",
  "description": "A Claude Code plugin",
  "version": "1.0.0",
  "author": {
    "name": "Your Name"
  },
  "homepage": "",
  "repository": "",
  "license": "MIT"
}
```

### Step 4: サンプルコマンドの生成

`commands/hello.md` を以下の内容で作成:

```markdown
---
description: Greet the user with a friendly message
---

# Hello Command

Greet the user warmly and ask how you can help them today.
Make the greeting personal if a name is provided via $ARGUMENTS.
```

### Step 5: hooks.json の生成

`hooks/hooks.json` を以下の内容で作成:

```json
{
  "hooks": {}
}
```

### Step 6: README.md の生成

`README.md` を以下の内容で作成:

```markdown
# <plugin-name>

A Claude Code plugin.

## Installation

```bash
claude /plugin install <path-to-plugin>
```

## Commands

- `/<plugin-name>:hello` - Greet the user

## Development

### Testing locally

```bash
claude --plugin-dir ./<plugin-name>
```

### Adding new commands

Add Markdown files to the `commands/` directory. The filename becomes the command name.

### Adding skills

Add `SKILL.md` files to subdirectories in `skills/`.

### Adding hooks

Configure event handlers in `hooks/hooks.json`.

## License

MIT
```

### Step 7: .gitkeep ファイルの作成

空ディレクトリを保持するため:

```bash
touch "${PLUGIN_NAME}/agents/.gitkeep"
touch "${PLUGIN_NAME}/skills/.gitkeep"
```

## 完了確認

生成後、以下を確認:

1. ディレクトリ構造が正しく作成されている
2. plugin.json に正しいプラグイン名が設定されている
3. README.md にプラグイン名が反映されている

## 使用例

```
/plugin-scaffold my-awesome-plugin
```

出力:

```
my-awesome-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   └── hello.md
├── agents/
│   └── .gitkeep
├── skills/
│   └── .gitkeep
├── hooks/
│   └── hooks.json
└── README.md
```

## 注意事項

- プラグイン名は kebab-case を推奨
- `.claude-plugin/` には plugin.json のみ配置（他のディレクトリは配置しない）
- 生成後、plugin.json の author.name を適切に編集すること
