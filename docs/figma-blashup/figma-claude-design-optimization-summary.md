# Figma デザイン構造整理の自動化 — 調査まとめ

## 課題

Figma to Code の再現率はデザインファイルの構造品質に大きく依存する。
クライアントから受け取るデザインはコンポーネント化・フレーム化・グループ化が不十分なケースが多く、
この整理作業を自動化したい。

---

## 結論：公式MCPでは構造整理はできない

Figma公式MCP Serverの全13ツールはすべて「読み取り」または「コード生成」方向。
既存デザインの構造変更（グループ化・Auto Layout適用・リネーム等）を行うツールはゼロ。
`generate_figma_design` も「コードから新規フレーム生成」であり、既存デザインの構造整理ではない。

参考：Figma MCP Server全13ツール解説
https://zenn.dev/aria3/articles/figma-mcp-server-tools-review

→ **構造整理の書き込みには別のアプローチが必要**

---

## ツール整理：何が何か

混同しやすいので整理。

| ツール | 何か | 役割 |
|---|---|---|
| **Figma公式MCP** | Figmaのデザインデータを読み取りコード生成するMCPサーバー | 読み取り（書き込み不可） |
| **Chrome DevTools MCP** | Chrome DevTools Protocolを通じてChromeブラウザを制御するMCPサーバー | ブラウザ版Figma上でPlugin APIをJS実行 |
| **Claude in Chrome** | Anthropicのブラウザ拡張機能。Coworkと組み合わせてブラウザ操作を自動化 | 画面を「見て」クリック・入力する |
| **claude-talk-to-figma-mcp** | コミュニティ製。WebSocket + Figmaプラグイン経由でFigma操作 | 読み書き可能だが今回は不要 |

### Chrome DevTools MCP と Claude in Chrome の違い

- **Chrome DevTools MCP**: Chrome DevTools Protocolで接続し、JSコードを直接実行。高速・正確。
- **Claude in Chrome**: 画面を視覚的に認識してマウス操作を模倣。遅い・UIの変更に弱い。

→ 構造整理の実行は Chrome DevTools MCP、結果の視覚的検証は Cowork + Claude in Chrome。

### デスクトップアプリの制約

Chrome DevTools MCP が操作できるのは **Chromeブラウザ**。
Figmaデスクトップアプリ（Electron）に外部から接続してPlugin APIを叩くのは困難。
デスクトップアプリ経由でPlugin APIを操作するには、Figmaプラグインを中継役にする
claude-talk-to-figma-mcp が必要になるが、WebSocket中継でレイテンシが出る・
用意されたコマンドの範囲に制約される。

→ **自動化ステップだけ同じファイルをChromeで開いて実行する方式が最適解**
→ Figmaはクラウドベースなので、デスクトップアプリとブラウザで同じファイルを同時に開ける。
  変更はリアルタイム同期される。普段のデスクトップアプリ作業を変える必要はない。

---

## 既存サービスの選択肢

### Locofy Lightning（Figma側を整理してからコード化）

- Figmaプラグインとして動作
- AIがデザインパターンを識別し自動実行：
  - Auto Layoutの自動適用
  - レイヤーのグループ化
  - コンポーネントのタグ付け
  - 複数スクリーンへのレスポンシブマッピング
- 無料プランあり / 有料は月$39〜
- 複雑なアニメーション・深いネスト構造には限界あり

### Builder.io Visual Copilot（構造が汚くてもコード側で吸収）

- 200万以上のデータポイントで学習した専用AIモデル
- Auto Layout未設定でもAIがデザインパターンを認識してコード構造に変換
- Figma側を一切触らずにコード精度を上げるアプローチ
- React, Vue, Svelte, Angular, HTML + 各種CSSライブラリ対応

### Codia AI / Anima

- 主に「新規生成」寄り。既存デザインの構造整理というよりFigma to Codeの別ルート

---

## 自前実装の方針

### 基本戦略：人間がセクション分け → AIが内部を整理

セクション境界の判断はデザイン意図の理解が必要なので人間がやる（5〜10分/ページ）。
セクション内の整理（リネーム・子グループ化・Auto Layout適用）は座標・サイズから
機械的に推論可能なのでAIに任せる。

### 最適ツール構成

| 工程 | ツール | 理由 |
|---|---|---|
| Step 0: ファイル全体の構造把握 | Claude Code + Figma公式MCP | `get_metadata` + `get_screenshot` で分析。公式だけあってデータ信頼性が高い |
| Step 1: セクション分け | 人間 / デスクトップアプリ（5〜10分） | Step 0のレポートを参考にFrameで囲む。いつも通りの操作感 |
| Step 2: セクション内の構造整理 | Claude Code + Chrome DevTools MCP | Chromeで同じファイルを開きPlugin API直叩き。JS一括実行で最速・最も柔軟 |
| Step 3: 結果の検証 | Cowork + Claude in Chrome | 整理後のファイルを視覚的にチェック（Auto Layoutの効き、レスポンシブ確認） |
| Step 4: コード生成 | Claude Code + Figma公式MCP | 整理済みフレームを `get_design_context` でコード化。構造整理済みなので精度向上 |

### 作業イメージ

```
1. デスクトップアプリでブランチを作成
2. デスクトップアプリでセクション分け（いつも通り）
3. 同じファイル（ブランチ）をChromeで開く ← ここだけブラウザ
4. Claude Code + Chrome DevTools MCP で構造整理を実行
5. デスクトップアプリ側で結果を確認（リアルタイム同期される）
6. 問題なければマージ
```

### Step 2の詳細（メインの自動化部分）

Chrome DevTools MCP経由でFigma Plugin APIを直接JSで実行。
1つのevaluate_scriptで複数操作をまとめて実行できるため、
WebSocket中継方式（claude-talk-to-figma-mcp）より高速・柔軟。

Claudeに以下のようなスクリプトを生成させる：

```js
// セクションFrame内の子要素を分析して整理
const section = figma.currentPage.selection[0];
const children = section.children;

// 1. 座標の近接性・サイズの類似性からグルーピング候補を推定
// 2. 関連要素をGroupまたはFrameに変換
// 3. Auto Layout適用（配置方向・Gap・Padding推定）
// 4. セマンティックなレイヤーリネーム
```

### CLAUDE.mdルールファイル（案件ごとに育てる）

```markdown
# Figma構造整理ルール

## リネーム規約
- セクション: section-{name} (例: section-hero, section-about)
- カード: card-{name}
- ボタン: btn-{variant} (例: btn-primary)
- 画像: img-{description}
- テキスト: txt-{role} (例: txt-heading, txt-body)

## Auto Layout
- カード横並び: horizontal, gap: 24, padding: 0
- セクション内: vertical, gap: 48, padding: 80 0
- ナビゲーション: horizontal, gap: 16, align: center
- フッター: vertical, gap: 24, padding: 48 0

## コンポーネント化基準
- 3回以上繰り返すパターンはComponent化
- ヘッダー/フッターは必ずComponent
- ボタンはvariant付きComponent（primary/secondary/outline）
```

---

## Figmaプラン要件

| ツール | 必要なシート |
|---|---|
| Figma公式MCP（Step 0, 4で使用） | Dev or Full（有料プラン） |
| Chrome DevTools MCP（Step 2で使用） | 不問（無料でもOK） |
| Cowork + Chrome（Step 3で使用） | 不問 |

→ **Devモードは使えた方がよい**（Step 0の分析精度とStep 4のコード生成精度に影響）

---

## 段階的アプローチ

### Phase 1: 分析レポート（リスクゼロ）
公式MCPでレイヤーツリーを読み出し、構造上の問題点をレポート化。
手動整理の指針として使える。

### Phase 2: リネーム自動化（低リスク・効果大）
レイヤー名のセマンティック化。構造を壊さずFigma to Codeの精度に直結。
最もコスパが良い。

### Phase 3: グループ化・Frame化（中リスク）
座標の近接性・スタイルの類似性から要素群を推定してGroup/Frameに変換。
ブランチ上で実行する前提。

### Phase 4: Auto Layout適用（高難度）
Frame化した要素に方向・Gap・Paddingを自動推定して適用。
座標配置からの推論がLocofyの専用Large Design Modelに相当する部分。
コーポレートサイト程度の定型レイアウトなら精度は出せる見込み。

---

## セットアップ

### 事前準備チェックリスト

1. Chrome DevTools MCPの確認・導入
   ```bash
   # 確認
   claude mcp list
   # 入ってなければ追加
   claude mcp add chrome-devtools npx chrome-devtools-mcp@latest
   ```

2. Figma公式MCPの確認（すでに導入済みの前提）
   ```bash
   claude mcp list  # figma が表示されればOK
   ```

3. 対象ファイルのブランチを作成（デスクトップアプリでOK）

4. 同じファイル（ブランチ）をChromeブラウザで開く

5. Figmaブラウザ版でPlugin APIを有効化
   - Chrome DevToolsのコンソールから `figma` と入力して確認
   - `figma is not defined` が出た場合：何か適当なプラグインを一度開いて閉じる
     （`figma` グローバルオブジェクトが未初期化になるFigma側のバグ）
   - ファイルの編集権限がない場合も `figma is not defined` になる
     → 新しいブランチを作成すると解決することがある

### はじめての実行フロー（Phase 1〜2推奨）

**Step 1: 分析だけ試す（リスクゼロ）**

Claude Codeで以下のように指示：
```
Chromeで開いているFigmaファイルのこのページのレイヤー構造を分析して、
構造上の問題点をリストアップして。
（例：フラットに並んでいる要素、命名されていないレイヤー、グループ化すべき要素群）
```

**Step 2: リネームだけ試す（低リスク・効果大）**

分析結果を確認した上で：
```
このセクション内のレイヤー名をセマンティックにリネームして。
命名規約：
- セクション: section-{name}
- カード: card-{name}
- ボタン: btn-{variant}
- 画像: img-{description}
```

→ デスクトップアプリ側でリネーム結果がリアルタイム反映されるのを確認

**Step 3: グループ化を試す（中リスク）**

リネームがうまくいったら：
```
このセクション内の要素を座標とサイズから分析して、
関連する要素をグループ化して。ブランチ上で作業しているので安全。
```

**Step 4: Auto Layout適用（高難度）**

グループ化がうまくいったら：
```
グループ化したFrameにAuto Layoutを適用して。
配置方向・Gap・Paddingは要素の座標配置から推定して。
```

---

## ハマりやすいポイント

### `figma is not defined` が出る

- ブラウザ版Figmaで一度何かプラグインを開いて閉じる（初期化トリガー）
- ファイルの編集権限を確認（閲覧のみだとPlugin APIにアクセスできない）
- ブランチを新規作成すると解決する場合がある

### Chrome DevTools MCPが接続できない

- Chromeが `--remote-debugging-port` 付きで起動しているか確認
- Chrome DevTools MCPは自動でChromeを起動するが、既に開いているChromeとは別インスタンスになる
- Figmaにログイン済みの状態でファイルを開く必要がある
  → 認証済みプロファイルで起動したい場合は `--user-data-dir` で専用プロファイルを作成

### 自動化中にデスクトップアプリと競合する

- Plugin API経由の変更中にデスクトップアプリ側で同じ要素を編集すると競合する
- 自動化ステップ実行中はデスクトップアプリ側で待機する
- 完了後にデスクトップアプリ側で結果を確認

---

## 注意事項

- 構造変更は必ずFigmaブランチ上で実行し、確認後にマージ
- CLAUDE.mdのルールは2〜3案件で育てることで安定化
- Chrome DevTools MCP使用時、Figmaへのログイン状態が必要（セッション情報に注意）
- 自動化ステップ中はデスクトップアプリ側で同じ要素を編集しない（競合回避）

---

## 参考リンク

- Figma公式MCP Server ドキュメント: https://developers.figma.com/docs/figma-mcp-server/
- 全13ツール解説（日本語）: https://zenn.dev/aria3/articles/figma-mcp-server-tools-review
- Chrome DevTools MCP: https://github.com/ChromeDevTools/chrome-devtools-mcp
- Plugin API直叩きの解説: https://cianfrani.dev/posts/a-better-figma-mcp/
- Locofy: https://www.locofy.ai/
- Builder.io Visual Copilot: https://www.builder.io/blog/figma-to-code-visual-copilot
- Figma Plugin API Reference: https://developers.figma.com/docs/plugins/api/global-objects/
