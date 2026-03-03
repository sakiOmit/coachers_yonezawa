# Delivery Checklist Criteria

## 自動チェック定量的基準

delivery-check.sh が実行する6項目の成功基準:

| チェック項目 | 定量的基準 | PASS条件 |
|-----------|----------|---------|
| Build | `npm run build` exit code | 0（エラーなし） |
| SCSS Lint | `npm run lint:scss` エラー数 | 0（警告はOK） |
| Image Size | 画像ファイルサイズ | すべて < 500KB |
| SEO | meta要素確認 | 全ページに title + meta description |
| Security | デバッグコード検出 | 0（console.log, var_dump 等なし） |
| PHP Syntax | `php -l` exit code | 0（構文エラーなし） |

**スクリプト実行例**:
```bash
bash .claude/skills/delivery/scripts/delivery-check.sh
# → reports/delivery-auto-20260303-143052.json 生成
```

## Output Examples

各サブコマンドの実行結果例:

### `/delivery check` 出力例

```
✅ Build: PASS (0 errors)
✅ SCSS Lint: PASS (0 errors, 2 warnings allowed)
⚠️  Image Size: 2 images > 500KB (hero.webp: 650KB, banner.webp: 720KB)
❌ SEO: Missing meta description on 3 pages (top, about, contact)
⚠️  Security: 5 debug code instances (console.log x3, var_dump x2)
✅ PHP Syntax: PASS (0 errors)

Result: 3/6 checks passed
Auto-fixable: 5 issues (security, seo)
Manual review required: image optimization, debug code removal

Checklist generated: reports/delivery-checklist-20260303.md
```

### `/delivery fix` 出力例

```
【修正対象】security-001: console.log in src/js/main.js (line 45, 62, 78)
  Status: auto-fixable
  Priority: HIGH

修正中...
✅ src/js/main.js: 3x console.log を削除
✅ チェックリスト更新

次の課題:
【修正対象】seo-002: meta description missing on page-about.php
  Status: manual
  Priority: HIGH
```

### `/delivery verify` 出力例

```
【手動確認】PC 実機テスト
  Status: pending
  Required: スマートフォンで top ページを確認

  - ヘッダー表示: [ ] OK [ ] NG
  - ナビゲーション展開: [ ] OK [ ] NG
  - 画像読み込み: [ ] OK [ ] NG

結果を入力してください（OK / NG / SKIP）：
```

### `/delivery report` 出力例

```
✅ 納品レポート生成中...

生成結果:
- reports/delivery-report-20260303.md（社内用）
- reports/delivery-report-client-20260303.md（クライアント用）

品質サマリー:
  自動チェック: 3/6 PASS
  手動確認: 8/10 OK
  残存課題: 5 items

納品承認欄:
  QA チェック: [QA担当者名]
  クライアント確認: [クライアント名]
```
