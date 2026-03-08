# Error Handling

figma-prepare スキルのエラーシナリオ、フォールバック動作、リカバリー手順。

## エラー一覧

| Error | Detection | Response |
|-------|-----------|----------|
| Invalid Figma URL | Regex parse failure | URL形式を表示 |
| get_metadata failure | MCP exception | 3回リトライ → エラー表示 |
| Chrome DevTools MCP 未登録 | .mcp.json チェック | Phase 1のみ実行 + セットアップ案内 |
| `figma` グローバル未初期化 | `typeof figma !== 'object'` | プラグイン開閉を案内 |
| Stage B スクリーンショット失敗 | get_screenshot MCP exception | Stage B スキップ + 警告表示 + 手動セクショニング推奨 |
| Stage C Haiku 推論失敗（個別） | Haiku API エラー or YAML パース失敗 | 該当セクションのみ Stage A にフォールバック |
| Stage C Haiku 推論失敗（全体） | 全セクションで Haiku 失敗 | Stage C スキップ → Stage A のみで進行 |
| Stage C ID 検証失敗 | node_ids 合計不一致 or ID 不在 | 該当セクションのみ Stage A にフォールバック |
| Node ID not found | evaluate_script 結果 | 個別スキップ + 警告 |
| バッチタイムアウト | evaluate_script タイムアウト | バッチサイズ縮小して再試行 |
| clone() 失敗 | evaluate_script 結果 success=false | エラー表示 + 中止 |
| IDマッピング不整合 | nameMatchRate < 0.95 | 警告表示 + 続行確認（AskUserQuestion） |
| リネームマップ ID 変換失敗 | mapping に存在しない ID | 個別スキップ + 警告 |

## Stage B スクリーンショット失敗時の警告

```
⚠️ Stage B (Claude sectioning) をスキップしました。
   原因: スクリーンショットの取得に失敗
   影響: トップレベルのセクション分割は行われません。
         Stage A（9手法: proximity + pattern + spacing + semantic + zone + tuple +
         consecutive + heading-content + highlight）による
         ネストレベルのグルーピングのみ適用されます。
   推奨: Figma上で手動でセクショニングを行うか、
         スクリーンショット取得の問題を解決して再実行してください。
```

## Stage C フォールバック動作

| 条件 | 対応 |
|------|------|
| Stage B が未実行/失敗 | Stage C をスキップ（セクション情報なし） |
| Haiku 推論失敗（個別セクション） | 該当セクションのみ Stage A にフォールバック |
| Haiku 推論失敗（全セクション） | Stage C 全体をスキップ → Stage A のみで進行 |
| YAML パース/検証失敗 | 該当セクションのみ Stage A にフォールバック |

## リカバリー手順

### Chrome DevTools MCP セットアップ

```bash
bash .claude/skills/figma-prepare/scripts/start-chrome-debug.sh "{figma-url}"
```

### Figma プラグインが応答しない場合

1. Figma のプラグインパネルを閉じる
2. プラグインを再度開く
3. `typeof figma` が `"object"` を返すことを確認

### バッチタイムアウトのリカバリー

1. バッチサイズを 50 → 25 に縮小
2. 再試行
3. それでも失敗する場合: 個別ノードごとに実行

### IDマッピング不整合のリカバリー

nameMatchRate < 0.95 の場合:
1. 不一致ノードのリストを確認
2. コンポーネントインスタンスや非表示レイヤーによる差異かを確認
3. ユーザーに続行/中止を確認（AskUserQuestion）
