# /figma-prepare 既知の課題

FIXED / CLOSED 済みの課題は [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) に移動済み。

## OPEN Issues

### Issue 176: Stage B subsections ラッパーが未適用（--apply 時）

**Phase**: 2
**状態**: FIXED
**概要**: `sectioning-plan.yaml` の階層的 subsections（main-content 内の section-hero-area, section-concept-area, section-feature-grid 等）のラッパー FRAME が作成されない。トップレベル（l-header, main-content, l-footer）のみ適用され、main-content 内がフラットなまま残る。

**原因**: SKILL.md の Phase 2-4 適用手順が「apply-grouping.js で実行」としか記載しておらず、subsections の再帰的適用（レベルごとの apply-grouping + parent_id 再マッピング）の手順が欠如していた。

**修正**: SKILL.md に 2-4a〜2-4e を追加。sectioning-plan → grouping-plan 変換ロジック、レベル間 parent_id 再マッピング、全レベル検証を明文化。

**検証方法**: risou 構造（38:475）との diff で main-content 内の中間ラッパー（hero+about / concept系 / feature-grid / why-bondish）が作成されていることを確認

### Issue 177: `get_root_node` が Figma REST API 形式（nodes.{id}.document）を未対応

**Phase**: 全体
**状態**: FIXED
**概要**: `figma_utils.py` の `get_root_node()` が `{'nodes': {'38:718': {'document': {...}}}}` 形式を処理できず、全スクリプトが `total_nodes: 1` を返す。手動で `nodes.{id}` を抽出して別ファイルに保存する前処理が必要だった。

**原因**: REST API (`/v1/files/{fileKey}/nodes`) のレスポンス形式に `nodes` ラッパーがあるが、`get_root_node()` は `document` / `node` キーのみチェックしていた。

**修正**: `get_root_node()` に `nodes` キー検出ロジックを追加。`nodes` dict の最初のエントリの `document` を返す。

**検証方法**: `analyze-structure.sh` に raw API metadata を渡して `total_nodes > 1` であること確認

### Issue 178: Stage A がルートレベル候補を生成し Stage B と競合

**Phase**: 2
**状態**: FIXED
**概要**: `detect-grouping-candidates.sh` が `parent: "02_ABOUT_base"`（ルートフレーム名）のグルーピング候補を生成する（header, zone 等）。Stage B も同じルートレベルの要素をセクション分割するため、`--apply` 時に重複ラッパーが作成される。

**原因**: Stage A の root-level 検出器（`detect_header_footer_groups`, `detect_vertical_zone_groups`, `detect_consecutive_similar`, `detect_heading_content_pairs`）が `is_root=True` で実行されるが、SKILL.md は「Stage A = nested, Stage B = root-level」と定義。

**修正**: `detect-grouping-candidates.sh` に `--skip-root` フラグを追加。設定時、root のフレーム名と一致する `parent` を持つ候補をフィルタリング。

**検証方法**: `--skip-root` 有無で候補数を比較。`--skip-root` 時にルートレベル候補が0件であること確認。

### Issue 179: フラット構造でヘッダークラスターが未検出

**Phase**: 2
**状態**: FIXED
**概要**: `prepare-sectioning-context.sh` のヘッダー検出が幅 > 80% ページ幅のフレームのみ対象。フラット構造（ヘッダーが logo Vector + nav Text × 6 + CTA Frame に分解）では個々の要素が幅基準を満たさず、ヘッダーが検出されない。

**原因**: ヘッダー検出ロジックが単一の幅広フレームを前提としており、複数の小要素がヘッダーゾーン（y < 120px）に散在するパターンを未考慮。

**修正**: ヘッダーゾーン（HEADER_ZONE_HEIGHT = 120px）内の要素クラスターを検出し、`header_cluster_ids` としてヒントに追加。3+ TEXT ノードが同ゾーンに存在する場合にクラスターと判定。

**検証方法**: 38:718 メタデータでヘッダー要素8個（38:948, 38:940, 38:942-38:947）が `header_cluster_ids` に含まれること確認

### Issue 181: テーブル行構造のグルーピング未検出

**Phase**: 2
**状態**: FIXED
**概要**: フラットな兄弟要素が実際にはテーブル行を構成しているパターンで、行単位のグルーピングが検出されない。背景RECTANGLE（交互色）+ divider（高さ0のVECTOR）+ テキスト群がY座標帯で同一行を形成している。

**修正**: `detect_table_rows()` を `figma_utils.py` に追加。3+フル幅RECTANGLE（≥90%親幅）を行背景として検出、高さ≤2pxのVECTOR/LINEをdivider検出、TEXT要素をY中心オーバーラップで行に割り当て。Stage A の全レベルで実行。12件のユニットテスト追加。

**発見箇所**: `/strength` ページの `section-recommend-career` 内 `Group 6131`（65:1111、22子要素）
- 見出し: `Group 6132`（Y=371、「水道関連有資格者数」）
- 行1: Rectangle#E7EDF8(Y=439) + Vector(Y=439,h=0) + 「排水設備工事責任技術者」(Y=472) + 「291」(Y=463) + 「名」(Y=476)
- 行2: Rectangle#F8FBFF(Y=542) + Vector(Y=542,h=0) + 「給水装置工事主任技術者」(Y=575) + 「263」(Y=566) + 「名」(Y=579)
- 行3: Rectangle#E7EDF8(Y=644) + Vector(Y=644,h=0) + 「２級管工事施工管理技士」(Y=677) + 「52」(Y=668) + 「名」(Y=681)
- 行4: Rectangle#F8FBFF(Y=746) + Vector(Y=746,h=0) + 「1級管工事施工管理技士」(Y=779) + 「41」(Y=770) + 「名」(Y=783)
- 末尾divider: Vector(Y=848,h=0)

**提案**: `detect_table_rows()` を Stage A に追加
1. 兄弟要素にフル幅RECTANGLE（交互色）が3+個存在 → テーブル候補
2. 各RECTANGLEのY範囲内にあるTEXT/VECTOR要素を同一行としてグループ化
3. 行間のdivider（高さ≈0のVECTOR、フル幅）は行の区切りとして検出し、上の行に吸収
4. テーブル全体を `table-{slug}` ラッパーで包み、各行を `table-row-N` としてグルーピング

**検証方法**: Group 6131 で見出し1個 + 4行 + 末尾dividerが行単位にグループ化されること

**関連データ**: `.claude/cache/figma/prepare-metadata-2-46645.json`（/strength メタデータ）、`sectioning-plan-2-46645.yaml`（セクショニング結果）

### Issue 180: 背景レイヤー+コンテンツレイヤーのグルーピング未検出

**Phase**: 2
**状態**: FIXED
**概要**: 親フレーム内で「背景 RECTANGLE（フル幅 SOLID fill）+ 同色装飾（吹き出し三角等）」と「コンテンツ要素（見出し + テキスト + イラスト + ボタン）」が混在するパターンで、背景レイヤーとコンテンツレイヤーを分離検出できない。

**修正**: `detect_bg_content_layers()` を `figma_utils.py` に追加。フル幅RECTANGLE（≥80%親幅、≥30%親高さ、リーフノード）を背景検出、小VECTOR/ELLIPSE（面積<5% bg）を装飾として吸収、残りをコンテンツとして分離。Stage A の非ルートレベルで実行。12件のユニットテスト追加。

**発見箇所**: `/strength` ページ (2:46645) の `section-recommend-local` (65:921 / 元 2:47295 = Group 6027)
- `Rectangle 794`: 1239×275、fill=#F5F5F5 — 背景帯
- `Vector 4`: 52×40、fill=#F5F5F5 — 吹き出し三角（装飾、同色）
- `Group 6030`: 「地元で働きたい方」見出し — コンテンツ
- TEXT: 説明文 — コンテンツ
- `Mask group`: イラスト — コンテンツ
- `Group 6004`: 「営業所一覧をみる」ボタン — コンテンツ

**提案**: `detect_bg_content_layers()` を Stage A に追加
1. 親幅の80%以上を占める RECTANGLE で SOLID fill → `bg-layer` 候補
2. 同色 fill の小要素（VECTOR等）→ bg-layer に吸収
3. 残りの要素 → `content-layer` としてグループ化

**検証方法**: `/strength` の recommend-local セクションで背景2要素 + コンテンツ4要素に分離されること。他ページでの同パターン出現頻度を確認後に汎用化判断。

**関連データ**: `.claude/cache/figma/prepare-metadata-2-46645.json`（/strength メタデータ）、`sectioning-plan-2-46645.yaml`（セクショニング結果）

### Issue 182: ビューポート外要素（off-canvas）のフィルタリング未対応

**Phase**: 1, 2
**状態**: FIXED

**修正**: `is_off_canvas()` を `figma_utils.py` に追加（`OFF_CANVAS_MARGIN = 1.5`）。`analyze-structure.sh` の `count_nodes()` で depth=1 の off-canvas ノードをスキップし `off_canvas_nodes` メトリクスとして報告。`detect-grouping-candidates.sh` でもルートレベルの off-canvas ノードをフィルタ。12件のユニットテスト + 4件の統合テスト追加。
**概要**: ページ幅（1440px）を大きく超えた位置に配置された要素（x=3557 等）が通常の要素と同等に扱われ、スコアリング・グルーピング・リネームの全フェーズで誤った結果を引き起こす。completely off-canvas な要素は未使用アセットや作業用コピーの可能性が高い。

**発見箇所**: トップ_0510修正 (2:8315)
- `Image` (ROUNDED-RECT, 1440×1886, **x=3557**, y=5657) — ページ右外に完全に配置
- `AdobeStock_541586693` (ROUNDED-RECT, **x=1598**, y=3784) — 右端が viewport 外にはみ出し
- `Group 70` (FRAME, **x=1279**, y=3987) — 右端が部分的にはみ出し

**提案**:
1. `analyze-structure.sh` に off-canvas 検出指標を追加:
   - `off_canvas_count`: x + w < 0 または x > page_width のノード数
   - `partial_overflow_count`: x < 0 または x + w > page_width だが完全に外ではないノード
2. Phase 2 の `walk_and_detect()` で完全 off-canvas ノードをスキップ（`visible: false` と同様）
3. 閾値: `OFF_CANVAS_THRESHOLD = page_width * 1.5`（要素の x 座標が閾値超過でスキップ）

**検証方法**: トップ_0510修正のメタデータで x=3557 の Image が Phase 1 の total_nodes から除外され、Phase 2 のグルーピング候補に含まれないこと

### Issue 183: 親幅超過要素（oversized elements）のグルーピング誤分類

**Phase**: 2
**状態**: FIXED
**概要**: ページ幅（1440px）を超える width を持つ要素が、zone グルーピングや semantic 検出で他の通常サイズ要素と混在して検出される。これらは意図的な「はみ出し」デザイン（写真が左右にはみ出す演出）であり、背景レイヤーとして扱うべきだが、現在の検出器は width > 1440 を特別扱いしない。

**修正**: `detect_bg_content_layers()` の bg 候補判定を拡張し、width >= `OVERFLOW_BG_MIN_WIDTH` (1400px) または x < 0 (左はみ出し、幅が親の50%以上) の RECTANGLE も背景候補として検出。`infer_zone_semantic_name()` でも width > `SECTION_ROOT_WIDTH` (1440) を `has_large_bg` 判定に追加。

**発見箇所**: トップ_0510修正 (2:8315)
- `赤パネル` (FRAME, **1943×937**, y=0) — hero 装飾パネル。幅がページ超過
- `Rectangle 69` (ROUNDED-RECT, **1652×538**, x=651, y=847) — 右側がはみ出し
- `AdobeStock_456066036 2` (ROUNDED-RECT, **1514×858**, x=**-140**, y=938) — 左側がはみ出し
- `AdobeStock_362745721 1` (ROUNDED-RECT, **1522×912**, x=64, y=1870) — 右端が超過
- `recruit_bg` (ROUNDED-RECT, **1422×578**, x=**-143**, y=2946) — 左側がはみ出し
- `image 385` (ROUNDED-RECT, **1800×823**, hidden=true) — hidden だが幅超過

**検証方法**: `赤パネル`、`Rectangle 69`、`AdobeStock_456066036 2` が zone 検出で bg 候補に分類され、コンテンツ要素と分離されること

### Issue 184: ニュースバー（横並び多要素フラットパターン）のグルーピング未検出

**Phase**: 2
**状態**: FIXED
**概要**: ニュースティッカー/バーのような UI パターンで、背景 RECTANGLE + アイコン Group + 複数 TEXT が全てルートレベルの兄弟として配置されている場合、現在の zone 検出は Y 座標の重なりでマージするが、「ニュースバー」というセマンティック単位として検出できない。各要素が小さく proximity group に入るが、意味的な一塊としての検出が弱い。

**修正**: `detect_horizontal_bar()` を `figma_utils.py` に追加（`HORIZONTAL_BAR_MAX_HEIGHT = 100`, `HORIZONTAL_BAR_MIN_ELEMENTS = 4`）。狭Y帯域（<100px）に4+要素が水平分布（X分散 > Y分散×3）し、1+背景RECTANGLEが存在するパターンを検出。テキスト内容から `news-bar` / `blog-bar` / `horizontal-bar` を推論。`walk_and_detect()` のルートレベルでヘッダー/フッター検出後、zone検出前に実行。4件のユニットテスト追加。

**発見箇所**: トップ_0510修正 (2:8315) の News bar (y=732-786)
- `Rectangle 1402` (821×74, x=64, y=732) — ニュースバー背景
- `Group 75` (35×35, x=1057, y=751) — 矢印アイコン
- TEXT `お知らせ一覧` (x=911, y=764)
- TEXT `2023.12.24...` (x=293, y=756) — ニュース内容
- TEXT `お知らせ` (x=196, y=759) — ラベル
- TEXT `NEWS` (x=98, y=753) — 英語ラベル
合計6要素が Y=732-786 の狭い帯域に並ぶ。

**検証方法**: 上記6要素が 1 つのグルーピング候補（`suggested_name: 'news-bar'`）として検出されること

### Issue 185: 英語ラベル + 日本語見出しペアのリネーム精度不足

**Phase**: 3
**状態**: FIXED

**修正**: `detect_en_jp_label_pairs()` を `figma_utils.py` に追加（`EN_LABEL_MAX_WORDS = 3`, `EN_JP_PAIR_MAX_DISTANCE = 200`）。`collect_renames()` で EN+JP ペア検出後、未命名の EN 側を `en-label-{slug}`、JP 側を `heading-{slug}` にリネーム。`JP_KEYWORD_MAP` に `会社情報→company-info`, `事業紹介→business`, `採用ブログ→recruit-blog` 追加。15件のテスト追加。
**概要**: 日本語セクション見出し（「会社情報」「事業紹介」「採用情報」等）の横や上に配置される英語ラベル TEXT（「COMPANY」「OUR BUSINESS」「RECRUIT」等）が、現在のリネームロジックで `text-company` や `label-our-business` のような汎用名に変換される。このペアは「セクション見出し装飾」としてより意味のある名前を付けるべきだが、2つの TEXT が独立した兄弟であるためペア検出できない。

**発見箇所**: トップ_0510修正 (2:8315)
- `会社情報` (TEXT, 297×101, x=136, y=1107) + `COMPANY` (TEXT, 51×169, x=1211, y=1155)
- `事業紹介` (TEXT, 291×101, x=385, y=1958) + `OUR BUSINESS` (TEXT, x=263, y=2275)
- TEXT `RECRUIT` + TEXT `採用情報`
- TEXT `BLOG` + TEXT `採用ブログ`

**提案**:
1. Phase 3 `infer_name()` に「英語+日本語見出しペア」検出を追加:
   - 同一 zone（Y 範囲が重なるか近接）に ASCII-only TEXT と 非ASCII TEXT が共存
   - ASCII TEXT が短い（1-3 単語）大文字表記
   - → ASCII 側を `en-label-{slug}`、日本語側を `heading-{slug}` にリネーム
2. `JP_KEYWORD_MAP` に `会社情報 → company-info`、`事業紹介 → business`、`採用ブログ → recruit-blog` を追加
3. 縦書き TEXT（width < height の TEXT）の検出を追加し、`vertical-label-{slug}` として命名

**検証方法**: `COMPANY` が `en-label-company`、`会社情報` が `heading-company-info` にリネームされること

### Issue 186: ブログカード（分離型カードパターン）のグルーピング未検出

**Phase**: 2
**状態**: FIXED

**修正**: `detect_repeating_tuple()` を `figma_utils.py` に追加（`TUPLE_PATTERN_MIN = 3`, `TUPLE_MAX_SIZE = 5`）。type列の繰り返しパターンを検出し `card-list-{slug}` としてグルーピング。Stage A の全レベルで実行。`METHOD_PRIORITY` に `tuple: 2.8` 追加。13件のユニットテスト追加。
**概要**: ブログセクションのカードが「画像 + テキスト情報 Group + ボタン Instance」の3要素に分離して配置されており、現在の `is_card_like()` では FRAME/COMPONENT/INSTANCE の子要素としてまとまっている場合のみ検出する。3要素がルートレベルの兄弟として並ぶ「分離型カード」パターンを検出できない。

**発見箇所**: トップ_0510修正 (2:8315) の Blog section (y=3697-4253)
3枚のカードが各々以下で構成:
- `AdobeStock_*` (ROUNDED-RECT/IMAGE) — カード画像
- `Group *` (FRAME) — カテゴリ + 日付 + タイトルのテキスト群
- `arrow` (INSTANCE) — 詳細ボタン

これらが 3×3 = 9 要素としてルートレベルに並び、pattern 検出は各要素タイプが異なるため構造ハッシュが一致せず、card 検出は3要素が1つの FRAME にラップされていないため `is_card_like()` が反応しない。

**提案**:
1. `detect_repeating_tuple()` を Stage A に追加:
   - 連続する N 個の兄弟がタプル単位で繰り返されるパターンを検出
   - 例: [IMAGE, FRAME, INSTANCE, IMAGE, FRAME, INSTANCE, IMAGE, FRAME, INSTANCE] → 3-tuple × 3回
   - タプルの structure_hash 列が 3+ 回繰り返されることを確認
2. 検出されたタプルグループは `card-list` として提案し、各タプルを `card-{index}` ラッパーで包む
3. 閾値: `TUPLE_PATTERN_MIN = 3` (最小繰り返し回数)、`TUPLE_MAX_SIZE = 5` (タプル最大サイズ)

**検証方法**: ブログセクションの9要素が 3-tuple × 3回として検出され、3つの card グルーピング候補が生成されること

### Issue 187: hidden 要素のスコアリング除外が不完全

**Phase**: 1
**状態**: FIXED

**修正**: `analyze-structure.sh` の `count_nodes()` に `visible == False` ガードを追加。hidden ノードのサブツリー全体をスキップし `hidden_nodes` メトリクスとして報告。`detect-grouping-candidates.sh` の `walk_and_detect()` でも hidden ノードスキップ + children フィルタリングを追加。3件の統合テスト追加。
**概要**: `visible: false` (`hidden=true`) の要素が Phase 1 のスコアリング（`count_nodes`）で通常の要素と同等にカウントされ、unnamed_rate や flat_sections を不正に膨張させる。Phase 3 の `collect_renames()` は `visible == False` をスキップする（Issue 145）が、Phase 1 は未対応。

**発見箇所**: トップ_0510修正 (2:8315)
- `image 385` (ROUNDED-RECT, 1800×823, **hidden=true**, y=0) — hero 背景の隠し画像
これが unnamed ノードとしてカウントされ、unnamed_rate を上昇させる。大規模ページでは hidden レイヤーが多数存在する可能性がある。

**提案**:
1. `analyze-structure.sh` の `count_nodes()` に `visible == False` ガードを追加（Phase 3 の `collect_renames()` と同様）
2. Phase 2 の `walk_and_detect()` でも hidden ノードをスキップ
3. 除外した hidden ノード数を `metrics` に `hidden_nodes` として報告

**検証方法**: `image 385` が total_nodes、unnamed_nodes から除外され、hidden_nodes=1 として報告されること

### Issue 188: 超フラット構造（85+直接子要素）のスコア精度検証

**Phase**: 1
**状態**: FIXED

**修正**: `flat_penalty` の上限を 30 → 40 に引き上げ。85 children (penalty=40) と 50 children (penalty=22.5) を区別可能に。`named_rate_pct` メトリクスを追加し、構造は悪いが命名は良いケースを識別可能に。`figma-prepare.md` のスコア計算式も同期更新。

### Issue 189: 装飾ドットパターン（小フレーム群）のリネーム/グルーピング

**Phase**: 2, 3
**状態**: FIXED

**修正**: `is_decoration_pattern()` + `decoration_dominant_shape()` を `figma_utils.py` に追加（`DECORATION_MAX_SIZE = 200`, `DECORATION_SHAPE_RATIO = 0.6`, `DECORATION_MIN_SHAPES = 3`）。Phase 3 の Priority 4.0 で ELLIPSE 多数なら `decoration-dots-{index}`、それ以外なら `decoration-pattern-{index}` にリネーム。18件のテスト追加。
**概要**: デザイン上の装飾ドットパターン（小さいフレームに複数の ELLIPSE/RECTANGLE が含まれる要素）が、各セクションに繰り返し出現する。現在のロジックでは各ドットフレームが `group-N` やフォールバック名で処理され、装飾要素としての意味が伝わらない。

**発見箇所**: トップ_0510修正 (2:8315)
- `ドット` (FRAME, 154×147, x=1393, y=743) — hero 右下の装飾ドット
- `Group 38` — business セクション内の装飾ドット
- `Group 57` — recruit セクション内の装飾ドット

これらは同じ視覚パターン（小丸の集合）だが、ルートレベルの別々の兄弟として配置されており、pattern 検出は構造ハッシュが一致する場合のみ。

**提案**:
1. Phase 3 `infer_name()` に装飾パターン検出を追加:
   - 子要素の大半が ELLIPSE で、全体サイズが小さい（< 200×200）→ `decoration-dots-{index}`
   - 子要素の大半が RECTANGLE で、全体サイズが小さい → `decoration-pattern-{index}`
2. 閾値: `DECORATION_MAX_SIZE = 200` (px)、`DECORATION_SHAPE_RATIO = 0.6` (60% が形状要素)
3. Phase 2 では装飾要素を nearest zone に吸収（現在の loose element 吸収と類似だが、高さ > 20px のフレーム対象）

**検証方法**: `ドット`、`Group 38`、`Group 57` が `decoration-dots-*` にリネームされること

### Issue 190: ハイライトテキストパターン（RECTANGLE 背景 + 重なり TEXT）の未検出

**Phase**: 2, 3
**状態**: FIXED

**修正**: `detect_highlight_text()` を `figma_utils.py` に追加（`HIGHLIGHT_OVERLAP_RATIO = 0.8`, `HIGHLIGHT_TEXT_MAX_LEN = 30`, `HIGHLIGHT_HEIGHT_RATIO_MIN = 0.5`, `HIGHLIGHT_HEIGHT_RATIO_MAX = 2.0`）。Stage A の非ルートレベルで実行。`METHOD_PRIORITY` に `highlight: 3.8` 追加。19件のテスト追加。
**概要**: テキストの一部を強調するため、TEXT の背後に RECTANGLE を配置するデザインパターンが存在する。この2要素は Z 方向で重なっており（同じ XY 範囲を占有）、現在の proximity/zone 検出では隣接要素として扱われるが、「ハイライトテキスト」というセマンティック単位として検出できない。

**発見箇所**: トップ_0510修正 (2:8315) の Recruit section
- `Rectangle 14` (205×49, x=217, y=3098) — ハイライト背景
- TEXT `会社の中核` — 強調テキスト（同位置に重なる）

同様のパターンはコーポレートサイトで頻出（数字の強調、キーワードハイライト等）。

**提案**:
1. `detect_highlight_text()` を Stage A に追加:
   - RECTANGLE と TEXT が同一 Y 範囲（80% 以上重なり）かつ RECTANGLE の幅が TEXT より狭いか同等
   - RECTANGLE の高さが TEXT の高さの 0.5-2.0 倍
   - TEXT が短い（30文字以下）
2. 検出されたペアを `highlight-{text-slug}` として命名
3. これは Issue 180 の bg-content 検出の小規模版とも言える

**検証方法**: `Rectangle 14` + `会社の中核` が highlight ペアとして検出されること

### Issue 191: フッター統合ラッパー（Group 745）内のサブセクション検出

**Phase**: 2
**状態**: FIXED

**修正**: `is_section_root()` の幅判定を緩和。`abs(width - SECTION_ROOT_WIDTH) < 10` → `width >= SECTION_ROOT_WIDTH * SECTION_ROOT_WIDTH_RATIO`（1296px 以上）。定数 `SECTION_ROOT_WIDTH_RATIO = 0.9` を追加。これにより `Group 745`（2433px 幅）もセクションルートとして検出され、`section_depth` が正しくリセットされる。テスト3件追加（oversized=2433, boundary=1296, below=1295）。
**概要**: ページ下部の「Contact + Footer Links + Bottom Bar + Sitemap」が1つの大きな Group (`Group 745`, 2433×1020) にラップされているが、内部の4つのサブセクション（`Group 589`: contact, `Group 723`: footer links, `Group 744`: bottom CTA bar, `Group 722`: sitemap + copyright）が Stage A のネスト走査で適切にグルーピング検出されない可能性がある。特に `Group 745` の幅が 2433px（ページ幅超過）であるため、`is_section_root()` の width 判定（|width - 1440| < 10）に合致せず、section_depth がリセットされない。

**発見箇所**: トップ_0510修正 (2:8315)
- `Group 745` (FRAME, **2433×1020**, y=4253) — 幅がページ超過
  - `Group 589` — contact area
  - `Group 723` — footer links
  - `Group 744` — bottom CTA bar (RECRUIT, partner logo, Instagram)
  - `Group 722` — sitemap + company info + copyright

**検証方法**: `Group 745` 内部の4サブグループがそれぞれセマンティック名で検出されること

### Issue 192: SNS/スクロールインジケーター縦型フレームのリネーム

**Phase**: 3
**状態**: FIXED

**修正**: `generate-rename-map.sh` の `infer_name()` に Priority 3.16 サイドパネル検出を追加（`SIDE_PANEL_MAX_WIDTH = 80`, `SIDE_PANEL_HEIGHT_RATIO = 3.0`）。幅≤80px かつ高さ>幅×3 でページ端に配置されたフレームを `side-panel-{index}` にリネーム。2件の統合テスト追加。
**概要**: ページ右端に縦型で配置される SNS リンク + スクロールインジケーター (`Frame 52`, 42×268, x=1379, y=315) が、現在のリネームロジックでは `group-N` やフォールバック名になる。このパターン（縦長・右端配置・小幅のフレーム）は企業サイトのデザインで頻出するが、専用の検出ロジックがない。

**発見箇所**: トップ_0510修正 (2:8315)
- `Frame 52` (FRAME, 42×268, x=1379, y=315) — SNS icons + scroll indicator

**提案**:
1. Phase 3 `infer_name()` に side-panel 検出を追加:
   - 幅が狭い（< 80px）かつ高さが幅の 3 倍以上
   - ページ右端（x > page_width * 0.9）または左端（x < page_width * 0.1）に配置
   - → `side-panel-{index}` または子要素テキストから `sns-indicator` 等
2. 閾値: `SIDE_PANEL_MAX_WIDTH = 80` (px)、`SIDE_PANEL_HEIGHT_RATIO = 3.0`

**検証方法**: `Frame 52` が `side-panel-0` または類似のセマンティック名にリネームされること

### Issue 193: CTA ボタン（お問い合わせ固定ボタン）の検出精度

**Phase**: 3
**状態**: FIXED

**修正**: `generate-rename-map.sh` の `infer_name()` に Priority 3.15 CTA 検出を追加（`CTA_SQUARE_RATIO_MIN = 0.8`, `CTA_SQUARE_RATIO_MAX = 1.2`, `CTA_Y_THRESHOLD = 100`）。正方形に近い形状 + ページ右上配置 + CTA キーワードテキスト（お問い合わせ, contact 等）で `cta-{slug}` にリネーム。2件の統合テスト追加。
**概要**: ページ右上に固定配置される CTA ボタン (`お問い合わせ`, 156×156, x=1259, y=22) が正方形のフレームで、現在のボタン検出ロジック（`BUTTON_MAX_HEIGHT = 70`, `BUTTON_MAX_WIDTH = 300`）の高さ制限を超過する（156px > 70px）。結果として `btn-*` ではなく `group-contact` 等にフォールバックする。

**発見箇所**: トップ_0510修正 (2:8315)
- `お問い合わせ` (FRAME, 156×156, x=1259, y=22) — 正方形 CTA ボタン

**提案**:
1. `infer_name()` に CTA 検出を追加:
   - 正方形に近い（幅と高さの差 < 20%）
   - ページ右上（x > page_width * 0.8 かつ y < 100）に配置
   - テキスト子要素に CTA キーワード（「お問い合わせ」「contact」等）を含む
   - → `cta-{slug}` として命名
2. 代替: BUTTON_MAX_HEIGHT を引き上げるのではなく、CTA は別カテゴリとして検出
3. `JP_KEYWORD_MAP` で `お問い合わせ → contact` は既存。ここでは位置ベースの検出を追加

**検証方法**: `お問い合わせ` フレームが `cta-contact` にリネームされること

## アーキテクチャ研究

### Issue 194: Phase B Claude推論のネストレベル拡張（Stage A 検出器の段階的置換）

**Phase**: 2（アーキテクチャ）
**状態**: OPEN
**優先度**: 高（設計方針の転換に関わる）

**背景**: Issue 180-193 の対応で Phase A (Stage A) にルールベースの検出器が急増している（`detect_table_rows`, `detect_repeating_tuple`, `detect_bg_content_layers`, `detect_highlight_text`, `detect_en_jp_label_pairs`, `is_decoration_pattern` 等）。新しいデザインパターンが出るたびに検出器を追加する「モグラ叩き」状態であり、スケーラビリティに問題がある。

**現状のアーキテクチャ**:
```
Phase A (ルールベース)                Phase B (Claude推論)
├─ ルートレベル: --skip-root          ├─ ルートレベルのみ担当
└─ ネストレベル: 12+個の検出器        └─ ネストレベルは担当外
    detect_table_rows()
    detect_repeating_tuple()
    detect_bg_content_layers()
    detect_highlight_text()
    ...永遠に増える
```

**提案するアーキテクチャ**:
```
Phase A (計測 + フィルタリング)        Phase B (Claude推論)
├─ hidden/off-canvas 除外             ├─ ルートレベル: セクション分割
├─ エンリッチドテーブル生成            └─ ネストレベル: パターン認識
│   (X座標, leaf判定, childTypes,         ↑ 再帰的にClaude呼び出し
│    flags, fill色)                       Haiku で十分な可能性
└─ 基本メトリクス計測
```

**Phase A に残すもの（確定的フィルタリング）**:
- hidden 要素の除外（Issue 187）
- off-canvas 要素の除外（Issue 182）
- メトリクス計測（スコアリング）
- エンリッチドテーブル生成

**Phase B に移行するもの（推論的パターン認識）**:
- カードパターン検出（Issue 186 → Claude が type 列の繰り返しを検出）
- テーブル行検出（Issue 181 → Claude が同一Y帯の RECT+TEXT 配列を検出）
- 背景+コンテンツ分離（Issue 180 → Claude がフル幅 RECT + 重畳要素を検出）
- ハイライトテキスト（Issue 190 → Claude が同座標の RECT+TEXT を検出）
- EN+JP ラベルペア（Issue 185 → Claude が大文字ASCII+日本語の近接ペアを検出）
- 装飾ドット（Issue 189 → Claude が小フレーム+ELLIPSE群を検出）
- ニュースバー（Issue 184 → Claude が狭Y帯の水平配列を検出）

**children table の改善（必須）**:

現状:
```
| # | ID | Name | Type | Y | W x H | Children | Unnamed | Text Preview |
```

提案:
```
| # | ID | Name | Type | X | Y | W x H | Leaf? | ChildTypes | Flags | Text |
```

追加カラム:
- **X座標**: 横並び・グリッド・はみ出しの検出に必須
- **Leaf?**: 背景RECT（子なし）とコンテナFRAMEの区別に必須
- **ChildTypes**: `1FRA+3TEX` 形式で子要素構成を表示。構造パターンの検出に必須
- **Flags**: `hidden`, `off-canvas`, `overflow`, `bg-candidate` 等の機械的フラグ

**実証実験の計画**:

1. **Phase 1: エンリッチドテーブルの有効性検証**
   - モデルケース（2:8315）のブログセクション（12要素）でテスト
   - エンリッチドテーブル + 簡易プロンプトで Claude (Haiku) にグルーピングを推論させる
   - Phase A 検出器の結果と比較し、一致率を計測
   - 目標: 80%以上の一致率

2. **Phase 2: ネストレベルの再帰的 Phase B**
   - ルートレベル Phase B の結果で得たセクション内部に対して、各セクションの children でもう一度 Phase B を実行
   - コスト計測: 入力/出力トークン数、Haiku での推論時間
   - 品質計測: Phase A 検出器群との結果比較

3. **Phase 3: 段階的移行**
   - Phase B で十分な精度が出た検出器から順に Phase A から削除
   - Phase A の検出器はプロンプトの few-shot examples として再活用
   - 移行後も回帰テストで品質を担保

**コスト試算**:
```
現状:  Phase B = 1回 (Opus, ルートのみ)
提案:  Phase B = 1回 (Opus, ルート) + N回 (Haiku, 各セクション)
       N ≈ 6セクション、各10-15要素 → Haiku 入力は小さい
       推定追加コスト: Haiku × 6 ≈ Opus × 0.3 程度
```

**検証方法**:
- 実証実験 Phase 1 の一致率が 80% 以上
- コスト増加が Opus 1回分の 50% 以内
- 新パターン（Phase A 未実装）に対しても正しく検出できること

**関連データ**:
- モデルケース: `.claude/cache/figma/prepare-metadata-2-8315.json`（72要素、超フラット構造）
- 既存プロンプト: `references/sectioning-prompt-template.md`
- ネストレベルプロンプト: `references/nested-grouping-prompt-template.md`（新規作成）
- エンリッチドテーブル生成: `lib/figma_utils.py` → `generate_enriched_table()`（新規作成）

**関連 Issue**: 180, 181, 184, 185, 186, 189, 190（全て Phase A 検出器として実装済み、Phase B 移行候補）

**Phase 1 実証実験結果（2026-03-05）**:

テスト対象: モデルケース（2:8315）から3セクション抽出、Haiku でグルーピング推論

| セクション | 要素数 | カバレッジ | ID正確性 | パターン検出 | グレード |
|-----------|--------|-----------|---------|-------------|---------|
| Blog（カード×4+ドット×2） | 11 | 11/11 (100%) | 100% | card✅ pagination✅ overflow✅ | A |
| Business（BG+見出し+カード×3+装飾） | 20 | 20/20 (100%) | 95%（ID1件ハルシネ） | bg✅ heading-pair✅ card✅ | B+ |
| Recruit（BG+見出し+ハイライト+CTA） | 11 | 11/11 (100%) | 100% | bg✅ heading-pair✅ highlight✅ cta✅ | A |

総合: **パターン検出率 91%（10/11）** — 目標80%を超過達成
コスト: Haiku×3 ≈ $0.009（Opus 1回の約3%）

**Haiku が正しく活用したエンリッチドテーブル情報**:
- `bg-full` フラグ → 背景レイヤー自動検出（3/3セクション）
- `tiny` フラグ → 装飾/ページネーション検出
- `overflow` フラグ → 画面外要素の認識
- `ChildTypes`（例: 1FRA+3TEX）→ カードパターンの繰り返し検出
- X座標 → 横並び配置の認識

**発見された課題**:
- Business セクションでIDハルシネーション1件（2:8514→正しくは2:8544）
- 対策: プロンプトに「テーブルのIDをそのままコピーせよ」の強調を追加
- 複雑なフラット構造（20要素、重複RECT）での精度がやや低下

**Phase 2 への推奨事項**:
- ネストレベル Phase B は Haiku で十分実用的
- IDハルシネーション対策のプロンプト改善
- `prepare-sectioning-context.sh` にエンリッチドテーブル生成を統合
- ルートレベル Phase B の children table もエンリッチド形式に移行

**Phase 2 実装結果（2026-03-05）**:

実装内容:
1. `prepare-sectioning-context.sh` に `--enriched-table` フラグを追加
   - フラグ指定時、`generate_enriched_table()` で生成したリッチ形式テーブルを `enriched_children_table` キーに出力
   - ルートレベル Phase B で `{children_table}` の代わりにエンリッチド形式を利用可能に
   - 引数パーサを `--output`/`--enriched-table` の順序非依存パースに改善
2. IDハルシネーション対策をプロンプトテンプレートに追加
   - `sectioning-prompt-template.md`: ルール2を「ID列をそのまま正確にコピー」に強化、照合確認を明記
   - `nested-grouping-prompt-template.md`: ルール2を同様に強化、ルール8「出力前にID照合」を追加
3. `sectioning-prompt-template.md` に enriched table 形式のドキュメントを追加
4. 後方互換性: `--enriched-table` 未指定時は従来の出力と完全一致（既存テスト37件+372件全通過）

発見された課題:
- なし（Phase 3 の段階的移行は次フェーズに委ねる）

**Phase 3 実装状況（2026-03-05）**:

Stage C（ネストレベル Claude 推論）の基盤スクリプトと比較ユーティリティを整備。

| コンポーネント | ファイル | 状態 | 担当 |
|---------------|---------|------|------|
| セクション別エンリッチドテーブル生成 | `scripts/generate-nested-grouping-context.sh` | DONE | 1号 |
| ノードID検索ユーティリティ | `lib/figma_utils.py` `find_node_by_id()` | DONE | 1号 |
| Stage A/C グルーピング比較 | `lib/figma_utils.py` `compare_grouping_results()` | DONE | 2号 |
| 比較スクリプト | `scripts/compare-grouping.sh` | 未着手 | 2号 |
| SKILL.md Stage C 統合 | `SKILL.md` / `phase-details.md` | 作業中 | 3号 |
| ユニットテスト: `find_node_by_id` | `tests/test_figma_utils.py` `TestFindNodeById` (7件) | DONE | 4号 |
| ユニットテスト: `compare_grouping_results` | `tests/test_figma_utils.py` `TestCompareGroupingResults` (10件) | DONE | 2号+4号 |
| 統合テスト: `generate-nested-grouping-context.sh` | `tests/run-tests.sh` Stage C セクション (2件) | DONE | 4号 |

テスト合計: 394件(unit既存) + 7件(find_node_by_id) = 401件(unit) + 39件(integration: 37既存+2 Stage C) = 440件

### Issue 196: マジックナンバー定数化漏れ（horizontal_bar, highlight）

**Phase**: 2, 3
**状態**: FIXED
**概要**: `detect_horizontal_bar` 内の水平分布判定 `x_var <= y_var * 3` および `detect_highlight_text` 内のX重なり判定 `x_overlap_ratio < 0.5` がハードコードされていた。
**発見箇所**: `figma_utils.py` L1268, L1175
**修正**: `HORIZONTAL_BAR_VARIANCE_RATIO = 3` と `HIGHLIGHT_X_OVERLAP_RATIO = 0.5` を定数化。figma-prepare.md 閾値テーブルに追加。

### Issue 197: `detect_heading_content_pairs` マジックナンバー 0.8

**Phase**: 2
**状態**: FIXED
**概要**: ヘッディング判定の中間ゾーン上限 `0.8` がハードコードされていた。
**発見箇所**: `figma_utils.py` L788
**修正**: `HEADING_SOFT_HEIGHT_RATIO = 0.8` を定数化。figma-prepare.md に追加。

### Issue 198: `walk_and_detect` で `get_bbox(node)` 二重呼び出し

**Phase**: 2
**状態**: FIXED
**概要**: `detect-grouping-candidates.sh` の `walk_and_detect` 関数内で、root ノードに対して `get_bbox(node)` が L612 と L628 で二重に呼び出されていた。
**発見箇所**: `detect-grouping-candidates.sh` L612, L628
**修正**: L628 を `page_bb = page_bb_pre` に変更し、既に計算済みの値を再利用。

### Issue 199: `_compute_child_types` TYPE_ABBR に IMAGE 欠落

**Phase**: 全体
**状態**: FIXED
**概要**: `figma_utils.py` の `_compute_child_types` 関数で、`TYPE_ABBR` マップに `IMAGE` タイプが欠落していた。IMAGE ノードが 'OTH' (Other) に分類され、enriched table のchildTypes列で情報が失われていた。
**発見箇所**: `figma_utils.py` L1707-1722
**修正**: `'IMAGE': 'IMG'` を TYPE_ABBR に追加。

### Issue 200: `generate-rename-map.sh` マジックナンバー `w < 1400`

**Phase**: 3
**状態**: FIXED
**概要**: カード検出のセクション除外判定で `w < 1400` がハードコードされていた。`OVERFLOW_BG_MIN_WIDTH` (1400) と同値だが定数参照していなかった。
**発見箇所**: `generate-rename-map.sh` L283
**修正**: `OVERFLOW_BG_MIN_WIDTH` をインポートし参照に変更。

### Issue 201: `prepare-sectioning-context.sh` ヒント関数内マジックナンバー

**Phase**: 2(B)
**状態**: OPEN
**概要**: `detect_heuristic_hints` 関数内に `page_h * 0.05`（ヘッダーゾーン5%）、`page_h * 0.9`（フッターゾーン90%）、`page_w * 0.8`（幅広判定80%）、`bb['h'] >= 100`（背景最小高さ）、`child_h > 200`（ヘッディング最大高さ）、`bb['h'] <= 20`（遊離要素高さ）等がハードコードされている。
**発見箇所**: `prepare-sectioning-context.sh` L87-184
**修正案**: Stage B Claude推論の補助ヒントであり、他の検出器の閾値テーブルとは独立した役割を持つ。Issue 194のアーキテクチャ移行後に整理するのが合理的。

### Issue 202: `infer-autolayout.sh` 定数がドキュメント未登録

**Phase**: 4
**状態**: OPEN
**概要**: `CENTER_ALIGN_VARIANCE = 4` と `ALIGN_TOLERANCE = 2` は Issue 148 で定数化されたが、figma-prepare.md の閾値テーブルに未登録のまま。
**発見箇所**: `infer-autolayout.sh` L31-32
**修正案**: figma-prepare.md の閾値テーブルに追加。

### Issue 203: `_compute_flags` 内マジックナンバー

**Phase**: 全体
**状態**: OPEN
**概要**: Issue 194 で新設された `_compute_flags` 関数内に `1.05`（overflow判定5%許容）、`1.02`（overflow-y 2%許容）、`0.95`（bg-full判定95%以上）、`50`（tiny判定50px未満）がハードコードされている。
**発見箇所**: `figma_utils.py` L1758-1780
**修正案**: 定数化して閾値テーブルに追加。ただし `_compute_flags` は enriched table 生成専用であり、スコアリングやグルーピングには影響しないため低優先度。

### Issue 204: `detect_bg_content_layers` left-overflow 判定がドキュメント未登録

**Phase**: 2
**状態**: OPEN
**概要**: Issue 183 で追加された left-overflow 検出条件 `bb['x'] < 0 and bb['w'] >= parent_bb['w'] * 0.5` の `0.5` が figma-prepare.md の閾値テーブルに未登録。
**発見箇所**: `figma_utils.py` L1356
**修正案**: figma-prepare.md に `bg_left_overflow_width_ratio | 0.5 (50%)` を追加。

### Issue 205: `detect_heading_content_pairs` 中間ゾーンの設計意図不明瞭

**Phase**: 2
**状態**: OPEN
**概要**: `HEADING_MAX_HEIGHT_RATIO` (0.4) と `HEADING_SOFT_HEIGHT_RATIO` (0.8) の間（40-80%）のヘッディングは外側の if を通過して `is_heading_like` チェックに進むが、この中間ゾーンが意図的な設計判断なのかが不明瞭。コメントに「40%未満は無条件で通過、40-80%は is_heading_like で追加検証、80%以上は除外」という三段階ロジックの設計意図を明記すべき。
**発見箇所**: `figma_utils.py` L786-789
**修正案**: コメントを追加して設計意図を明文化。

### Issue 206: `_split_by_spatial_gap` 非リーフグループ最小サイズ閾値

**Phase**: 2
**状態**: OPEN
**概要**: `_split_by_spatial_gap` 内の `if not all_leaf and len(nodes) < 6` の `6` が figma-prepare.md 閾値テーブルに未登録。Issue 88 で追加されたが文書化漏れ。
**発見箇所**: `detect-grouping-candidates.sh` L184
**修正案**: figma-prepare.md に `non_leaf_split_min_size | 6 elements` を追加。

---

## 改善方針

### 品質基準

- フィクスチャテスト: 全件パス（回帰防止）— 401件(unit) + 39件(integration) = 440件 (Issue 194 Phase 3: +7件unit find_node_by_id, +10件unit compare_grouping_results, +2件integration Stage C)
- キャリブレーション: Grade Accuracy 100%、全ケーススコア範囲内 — 8件
- 実データ: Phase 3 フォールバック率 0%（realistic fixture）
- ヘッダー/フッター検出: 100%（realistic fixture + INSTANCE/COMPONENT型対応）
- enriched metadata: IMAGE fill 判定 100%、layoutMode exact 100%
- characters フィールド活用: enriched TEXT のリネーム精度向上
- figma_utils.py ユニットテスト: 全 public 関数カバー（33 public + 6 private = 39関数、generate_enriched_table含む）
- 実データ検証: ABOUT ページ (38:718) で Phase 1-3 実行済み、理想構造 (38:475) と比較検証済み
- Stage B セクショニング精度: 10/10 セクション完全一致（Jaccard 1.0）、40/40 ノード ID カバレッジ 100%

### 次の改善候補

- **[最優先] Issue 194: Phase B Claude推論のネストレベル拡張** — アーキテクチャ転換の実証実験
- トップ_0510修正 (2:8315) モデルケースでのキャリブレーション（超フラット構造、Issue 188）
- 実プロジェクトでの `/figma-prepare --enrich` 実運用テスト（トークン消費計測含む）
- 複数ページ横断での共通ヘッダー/フッター自動検出
- 残 OPEN Issues: 194 (Phase B ネストレベル拡張), 201-206 (マジックナンバー/ドキュメント不整合)

### Issue 207: run-tests.sh シェル変数インジェクション（$SEMANTIC_FIXTURE）

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `run-tests.sh` の Phase 2 semantic fixture 生成部で、`$SEMANTIC_FIXTURE` がダブルクォート内の `python3 -c "..."` 文字列に直接埋め込まれていた。パスにスペースや特殊文字を含む場合にシェルインジェクションの危険性があった。
**発見箇所**: `run-tests.sh` L162
**修正**: `sys.argv[1]` パターンに変更し、`"$SEMANTIC_FIXTURE"` をコマンド引数として渡す方式に修正。Issue 64/95/112/130/139 と同じパターン。

### Issue 208: `_compute_zone_bboxes` テストカバレッジ欠如

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `_compute_zone_bboxes` は `detect-grouping-candidates.sh` のゾーンマージロジックの基盤関数だが、直接のユニットテストが存在しなかった。間接的にのみ検証されていた。
**発見箇所**: `test_figma_utils.py` — TestComputeZoneBboxes クラス不在
**修正**: `TestComputeZoneBboxes` クラスを追加（5テスト: single_group, multiple_groups, empty_groups, nonexistent_ids, single_member_group）。

### Issue 209: `detect_horizontal_bar` エッジケーステスト不足

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `detect_horizontal_bar` の既存テストは基本的な検出と定数チェックのみで、空配列入力、ブログバー命名、汎用バー命名、垂直配置非検出などのエッジケースが欠如していた。
**発見箇所**: `test_figma_utils.py` — TestDetectHorizontalBar クラス
**修正**: 6テスト追加（test_empty_children, test_blog_bar_naming, test_generic_bar_naming, test_variance_ratio_constant, test_vertically_stacked_not_detected, test_below_min_elements）。

### Issue 210: `detect_bg_content_layers` ELLIPSE装飾テスト欠如

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `detect_bg_content_layers` のテストでELLIPSE型ノードの装飾/コンテンツ判定の境界値テストが存在しなかった。小型ELLIPSEが装飾として分類されるか、大型ELLIPSEがコンテンツとして分類されるかの検証が不足。
**発見箇所**: `test_figma_utils.py` — TestDetectBgContentLayers クラス
**修正**: `TestDetectBgContentLayersEllipseDecoration` クラスを追加（2テスト: small_ellipse_as_decoration, large_ellipse_as_content）。

### Issue 211: `detect_repeating_tuple` 単一distinct type スキップのテスト欠如

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `detect_repeating_tuple` は distinct type 数が2未満のタプルをスキップするロジックがあるが、このエッジケースのテストが存在しなかった。
**発見箇所**: `test_figma_utils.py` — TestDetectRepeatingTuple クラス
**修正**: `TestDetectRepeatingTupleSingleDistinct` クラスを追加（2テスト: two_type_tuple_detected, same_type_pair_not_tuple）。

### Issue 212: qa-check.sh に Issue 180-193 検出器カバレッジチェック欠如

**Phase**: テスト基盤
**状態**: FIXED
**概要**: qa-check.sh の5つのチェックカテゴリでは、Issue 180-193 で追加された9つの検出器関数がテストファイルに存在するかの検証が行われていなかった。検出器を追加してもテスト未作成のまま見過ごされるリスクがあった。
**発見箇所**: `qa-check.sh` — check カテゴリ5つのみ
**修正**: チェックカテゴリ6「detector-coverage」を追加。9検出器（detect_bg_content_layers, detect_table_rows, detect_repeating_tuple, detect_en_jp_label_pairs, is_decoration_pattern, decoration_dominant_shape, detect_highlight_text, detect_horizontal_bar, generate_enriched_table）の test_figma_utils.py 内存在確認 + figma_utils.py 内定義確認。

### Issue 213: `generate_enriched_table` overflow_y エッジケーステスト欠如

**Phase**: テスト基盤
**状態**: FIXED
**概要**: `generate_enriched_table` の `overflow-y` フラグ（ノードがページ高さを超過する場合）のテストが存在しなかった。page_height=0 の場合の挙動も未検証。
**発見箇所**: `test_figma_utils.py` — TestGenerateEnrichedTable クラス
**修正**: `TestGenerateEnrichedTableOverflowY` クラスを追加（3テスト: overflow_y_with_page_height, no_overflow_y_within_page, zero_page_height_no_overflow_y）。

## 一覧

| Issue | Phase | 状態 | 概要 |
| ----- | ----- | ---- | ---- |
| 1-14 | — | **FIXED** | [RESOLVED-ISSUES.md](RESOLVED-ISSUES.md) 参照 |
| 15 | 1.5 | **FIXED** | `get_design_context` 補完パイプライン — `enrich-metadata.sh` 新設 |
| 16 | 2 | **FIXED** | ヘッダー/フッターのセマンティック推論強化 — Priority 3.1 追加 |
| 17 | 2 | **FIXED** | fills ベースの IMAGE 判定 — Priority 2 で fills チェック |
| 18 | 4 | **FIXED** | layoutMode 補完による Phase 4 精度向上 — exact confidence |
| 19 | 2 | **FIXED** | Phase 2 Stage B を Claude 推論ベースに拡張（セクショニング対応）— Stage B 追加 |
| 20 | 2,3 | **FIXED** | Before/After 検証を構造 diff ベースに変更 — verify-structure.js 新設 |
| 21 | 2,3 | **FIXED** | Phase 2/3 の実行順序入れ替え（Phase 2=グルーピング、Phase 3=リネーム） |
| 22 | 2 | **FIXED** | Phase 2 グルーピング精度 — dedup修正 + テストケース3件追加 |
| 23 | 2 | **CLOSED** | ネストグルーピング — 設計上 Stage B に委譲（Won't Fix） |
| 24 | 全体 | **FIXED** | 共通関数の Python ライブラリ化 — `lib/figma_utils.py` 新設 |
| 25 | 全体 | **FIXED** | `get_bbox` 返却キー名統一 — 共有 `get_bbox` に統合 + デッドコード除去 |
| 26 | 全体 | **FIXED** | ドキュメント Phase 番号不整合 + デッドコード除去 |
| 27 | 全体 | **FIXED** | YAML出力の特殊文字エスケープ — `yaml_str()` ヘルパー導入 |
| 28 | 全体 | **FIXED** | テストメッセージ Phase 番号不整合 + シェル変数インジェクション修正 |
| 29 | 2 | **FIXED** | page-kv 検出ロジックの二重定義 → 設計変更: page-kv 検出器自体を削除 |
| 30 | 2 | **FIXED** | `detect_semantic_groups` が enriched fills を考慮しない → 設計変更: semantic 検出器自体を削除 |
| 31 | 2 | **FIXED** | Stage A 簡素化による Stage B 依存度増加 — フォールバック警告追加 |
| 32 | 3 | **FIXED** | Priority 4 fills=[] IndexError — 安全な fills チェックに修正 |
| 33 | docs | **FIXED** | phase-details.md のドキュメント陳腐化 — 5箇所修正 |
| 34 | 全体 | **FIXED** | `SCRIPT_DIR` シェル変数インジェクション — `sys.argv` 経由に変更 |
| 35 | 3 | **FIXED** | `infer_name()` 内の `text_contents` 二重計算 — 単一ブロックに統合 |
| 36 | docs | **FIXED** | phase-details.md の `autolayout_penalty` 出力例が非ゼロ — 0 に修正 |
| 37 | 2,3 | **FIXED** | INSTANCE/COMPONENT/SECTION 型のヘッダー/フッター検出漏れ — 型チェック拡張 |
| 38 | 3 | **FIXED** | characters フィールド活用でリネーム精度向上 — enriched TEXT 優先 |
| 39 | 3 | **FIXED** | Priority 3 デッドコード文書化 — PAGE/CANVAS 限定の到達条件をコメント明記 |
| 40 | 1 | **FIXED** | Phase 1 スコアリングの detect_grouping_candidates 不一致を文書化 |
| 41 | 2 | **FIXED** | YAML出力の `'pattern'` キー誤り → `'structure_hash'` に修正 |
| 42 | docs | **FIXED** | sectioning-prompt-template.md の Phase 番号誤り（Phase 3 → Phase 2） |
| 43 | docs | **FIXED** | phase-details.md 信頼度テーブル更新 — `exact` 追加、`low` 削除 |
| 44 | 2,3 | **FIXED** | 未使用 import 削除 — `unicodedata`(Phase 3), `re`(Phase 2) |
| 45 | 全体 | **FIXED** | `to_kebab` + `JP_KEYWORD_MAP` コード重複 — `figma_utils.py` に統合 |
| 46 | docs | **CLOSED** | confidence 定義の不一致 — 調査の結果 phase-details.md は正しく更新済み（Not an Issue） |
| 47 | 3 | **FIXED** | `to_kebab` CamelCase 分割未実装 — `re.sub` で分割ロジック追加 |
| 48 | 全体 | **FIXED** | 深いネスト Figma ファイルで再帰制限クラッシュ — `sys.setrecursionlimit(3000)` 追加 |
| 49 | 全体 | **FIXED** | `get_text_children_content` / `get_text_children_preview` コード重複 — `figma_utils.py` に統合 |
| 50 | テスト | **FIXED** | `figma_utils.py` の `yaml_str`, `get_bbox`, `get_root_node` テスト未カバー — ユニットテスト追加 |
| 51 | テスト | **FIXED** | `to_kebab` エッジケーステスト不足 — 空文字列、日本語、CamelCase、特殊文字等のテスト追加 |
| 52 | 全体 | **FIXED** | `snap()` 関数コード重複 — `infer-autolayout.sh` から `figma_utils.py` に抽出 |
| 53 | 全体 | **FIXED** | `is_section_root()` 関数コード重複 — `analyze-structure.sh` から `figma_utils.py` に抽出 |
| 54 | docs | **FIXED** | phase-details.md リネームロジック優先順テーブルに Sub-priority 未記載 — 3.1/3.2/3.5 追加 |
| 55 | テスト | **FIXED** | `is_unnamed()` ユニットテスト未カバー — 12パターン+6非マッチのテスト追加 |
| 56 | テスト | **FIXED** | `resolve_absolute_coords()` ユニットテスト未カバー — 座標累積・リーフ・bbox欠損のテスト追加 |
| 57 | テスト | **FIXED** | `to_kebab` タブ・改行文字のテスト未カバー — chr(9)/chr(10)/chr(13) のテスト追加 |
| 58 | テスト | **FIXED** | `enrich-metadata.sh` 空エンリッチメント JSON のエッジケーステスト未カバー — テスト追加 |
| 59 | テスト | **FIXED** | `prepare-sectioning-context.sh` 子要素なしルートのエッジケーステスト未カバー — テスト追加 |
| 60 | 全体 | **FIXED** | `absoluteBoundingBox: null` で `get_bbox`/`is_section_root`/`resolve_absolute_coords` がクラッシュ — `or {}` ガード追加 |
| 61 | 2 | **FIXED** | `detect-grouping-candidates.sh` の YAML 出力に `suggested_wrapper` が欠落 — 出力行追加 |
| 62 | 全体 | **FIXED** | `get_text_children_content(filter_unnamed=True)` が `characters` でなく `name` で判定するよう修正 |
| 63 | 4 | **FIXED** | `layout_from_enrichment()` が exact な Figma 値を `snap()` で丸めていた — `int()` に変更 |
| 64 | テスト | **FIXED** | `run-tests.sh`/`qa-check.sh` の `printf "$ERRORS"` がフォーマット文字列として解釈される — 安全な方式に修正 |
| 65 | テスト | **FIXED** | `qa-check.sh` の `check_unused_imports` にサブシェル問題によるデッドコードループ — 削除 |
| 66 | docs | **FIXED** | `phase-details.md` Phase 3 前提条件「ブランチ必須」が SKILL.md の Adjacent Artboard 方式と矛盾 — 修正 |
| 67 | 全体 | **FIXED** | `resolve_absolute_coords` の二重呼び出しで座標が破損する — `_abs_resolved` マーカーで防止 |
| 68 | docs | **FIXED** | KNOWN-ISSUES.md の public 関数カウント（11→9）修正 |
| 69 | 4 | **FIXED** | `infer-autolayout.sh` が INSTANCE/COMPONENT ノードの Auto Layout 推論をスキップ — 型チェック拡張 |
| 70 | 4 | **FIXED** | `layout_from_enrichment` の `source` が base metadata でも `'enriched'` と表示される — ロジック修正 |
| 71 | 1 | **FIXED** | `analyze-structure.sh` の `max_depth` が絶対深度で報告されるがスコアは相対深度を使用 — `max_section_depth` 追加 |
| 72 | 1 | **FIXED** | `analyze-structure.sh` が INSTANCE 型ノードをフラット/深ネスト指標に含めない — 型チェック拡張 |
| 73 | docs | **FIXED** | SKILL.md Usage/Input Parameters に `--enrich` フラグ未記載 — ドキュメント追加 |
| 74 | 4 | **FIXED** | Phase 4 YAML 出力に `source` フィールドが欠落 — 出力行追加 |
| 75 | 4 | **FIXED** | `source` ラベルが `'enriched'` だがベースメタデータ由来も含む — `'exact'` に統一 |
| 76 | docs | **FIXED** | `.claude/rules/figma-prepare.md` に `max_section_depth` 指標の説明が未記載 — ドキュメント追加 |
| 77 | 3 | **FIXED** | Priority 3.1 nav検出の子要素タイプに INSTANCE/COMPONENT が含まれない — 型チェック拡張 |
| 78 | 2 | **FIXED** | 近接グルーピングが距離のみ判定で誤検出 — スコアリング化（距離×整列×サイズ類似） |
| 79 | 2 | **FIXED** | パターン検出が完全一致ハッシュで微差を見逃す — Jaccard類似度0.7でファジーマッチ |
| 80 | 2 | **FIXED** | 等間隔配置の検出手法がない — `detect_regular_spacing` (CV < 0.25) 追加 |
| 81 | 2 | **FIXED** | Stage Aに構造的セマンティック検出器がない — Card/Nav/Grid検出器追加（fills非依存） |
| 82 | 4 | **FIXED** | 2要素のAuto Layout方向判定が不安定 — `infer_direction_two_elements`（dx vs dy直接比較） |
| 83 | 4 | **FIXED** | WRAP/SPACE_BETWEEN/END未対応 — `detect_wrap`, `detect_space_between`, END alignment追加 |
| 84 | 4 | **FIXED** | 信頼度がchild数のみで判定 — gap CoVベース（< 0.15: high, 0.15-0.35: medium, >= 0.35: low） |
| 85 | 2 | **FIXED** | トップレベルのヘッダー/フッター構成要素が未グルーピング — `detect_header_footer_groups` をルートレベル限定で追加。ページ上端120px以内のナビTEXT+ロゴ/アイコン要素、下端300px以内の要素を検出。既に HEADER/FOOTER 名を持つ要素はスキップ |
| 86 | 2 | **FIXED** | 異種type要素の「セクション」グルーピング未対応 — `detect_vertical_zone_groups` をルートレベル限定で追加。Y座標範囲の重なり（50%以上）による垂直ゾーンマージで、異なるtypeの要素をセクション単位にグルーピング。method='zone'（priority=3、semantic=4とpattern=2の間） |
| 87 | 2 | **FIXED** | リーフノードのpattern誤検出 — children=[]のノード（TEXT等）が位置的に離れていても同一ハッシュで1グループになる。`_split_by_spatial_gap`で空間ギャップによるサブグルーピングを追加 |
| 88 | 2 | **CLOSED** | 大規模patternグループのサブグルーピング — 調査の結果、12枚カードのグリッド(3行×4列、行間30px)は1グループ維持が正しい（目標ページでも1セクション内に包含）。上位セクション分割はStage Bに委譲。`_split_by_spatial_gap`にグリッド検出(row_tolerance=20)を追加し大ギャップのみ分割するよう改善 |
| 89 | 1 | **FIXED** | Phase 1スコアリングがトップレベル子要素数を十分にペナライズしない — `flat_excess`指標追加（超過子要素数×0.5）。flat_penaltyを`flat_sections×5 + flat_excess×0.5`に変更、上限を-20→-30に拡大。フラット構造(40要素)のスコアが56.5→44.0に低下し構造化(3要素)60.9との差が拡大 |
| 90 | 全体 | **FIXED** | Phase 2-4の `--apply` 機能 — `apply-grouping.js`（ラッパーFrame作成+子要素移動）、`apply-autolayout.js`（layoutMode/gap/padding設定）新設。Phase 3の `apply-renames.js` は既存。全スクリプトがバッチ50件/回、ID存在チェック、エラーperノードスキップに対応 |
| 91 | 2 | **FIXED** | Zone検出のセマンティック命名 — `infer_zone_semantic_name` で子構造分析（hero/cards/grid/nav/content）。カウンタ付きサフィックス（cards-1, content-2等）で一意性保証。テスト追加（86件） |
| 92 | 2 | **FIXED** | `apply-grouping.js` の適用後検証スクリプト `verify-grouping.js` 新設 — ラッパーFRAME存在・名前一致、子要素移動確認、bbox整合性（±2px許容）の3項目を検証 |
| 93 | docs | **FIXED** | SKILL.md Phase 2/4 `--apply` セクションに `apply-grouping.js` / `apply-autolayout.js` のスクリプト名・手順を追記 |
| 94 | 4 | **FIXED** | `apply-autolayout.js` の適用後検証スクリプト `verify-autolayout.js` 新設 — layoutMode/layoutWrap、itemSpacing（±1px）、padding 4辺（±1px）、primaryAxisAlignItems、counterAxisAlignItems を検証。SKILL.md Phase 4-3、figma-plugin-api.md にドキュメント追加 |
| 95 | テスト | **FIXED** | `run-tests.sh` インライン Python 内のシェル変数インジェクション — `'${SCRIPT_DIR}'`/`'${SKILLS_DIR}'` を `os.environ[]` 経由に変更。`export SCRIPT_DIR SKILLS_DIR` 追加 |
| 96 | テスト | **FIXED** | `qa-check.sh` 関数外での `local` 宣言 — `--json` モードの `local tmp_issues tmp_warnings` を削除。`set -euo pipefail` 環境でのエラー回避 |
| 97 | docs | **FIXED** | `phase-details.md` フラット構造ペナルティ上限値が古い（-20→-30）— Issue 89 の `flat_excess` 追加を反映 |
| 98 | 4 | **FIXED** | `infer-autolayout.sh` の `source` 変数が未初期化 — `source = None` で先行初期化追加 |
| 99 | 2 | **FIXED** | `apply-grouping.js` のデッドソート比較関数（常に 0 を返す `.sort()`）— 不要な `.sort()` 呼び出しを削除 |
| 100 | 全体 | **FIXED** | `figma_utils.py` の関数内ラジーインポート（PEP 8 違反）— `Counter`, `statistics` をファイル先頭に移動 |
| 101 | 全体 | **FIXED** | `detect_regular_spacing()` の未使用パラメータ `tolerance` — パラメータ削除、CV_THRESHOLD 定数に統一 |
| 102 | テスト | **FIXED** | `qa-check.sh` dead-code チェックが `figma_utils.py` 内部使用関数を誤検出 — `alignment_bonus`, `size_similarity_bonus`, `_raw_distance` は `compute_grouping_score()` 内部で使用。チェッカーに内部使用判定（def行+呼び出し行で出現数>1）を追加 |
| 103 | docs | **FIXED** | `phase-details.md` Stage A 検出メソッドテーブルが陳腐化 — `semantic` の優先度が 3→4 に修正、`zone` メソッド（優先度 3）を追加 |
| 104 | 4 | **FIXED** | `infer_layout()` が counter_axis_align に 'END' を返すが Figma Plugin API は 'MAX' のみ受付 — verify-autolayout.js で検証失敗の原因。'END' → 'MAX' に修正、phase-details.md のドキュメントも更新 |
| 105 | 1 | **FIXED** | `analyze-structure.sh` の `score_breakdown.flat_penalty` が未丸め — `unnamed_penalty` は `round(..., 1)` だが `flat_penalty` は未丸め。一貫性のため `round(..., 1)` を追加 |
| 106 | docs | **FIXED** | `phase-details.md` line 139 が「セマンティック検出は Stage A から削除済み（Issue 29/30）」と記載しているが、Issue 81 で fills 非依存の構造ベースセマンティック検出として再追加済み。同一ファイル内の検出メソッドテーブル（lines 235-241）と直接矛盾。注意文を更新 |
| 107 | docs | **FIXED** | Phase 2 Stage A のメソッド一覧が不完全 — `phase-details.md` line 230 に "zone" 欠落、`SKILL.md` lines 351/369 が "proximity + pattern のみ" と記載。Issue 78-86 で追加された5手法（proximity + pattern + spacing + semantic + zone）に更新 |
| 108 | テスト | **FIXED** | `qa-check.sh` `doc-staleness` チェックが Stage A 検出メソッドの矛盾を検出できない — 「削除済み」記述の検出と SKILL.md のメソッド一覧不完全性チェックを追加 |
| 109 | 2 | **FIXED** | `apply-grouping.js` の `absoluteTransform` null チェック欠落 — 子ノードの bbox 計算（line 104）と位置変換（lines 149-152）で `absoluteTransform` に null ガード追加。親ノードは既にガード済み（lines 129-130）だが子ノードは未対応だった |
| 110 | 2 | **FIXED** | `apply-grouping.js` デッドコード `origX`/`origY` — `childOrder` の map で取得・destructure されるが未使用。map を削除し直接 `childNodes` をイテレート |
| 111 | テスト | **FIXED** | `run-tests.sh` 4px スナップテストが `exact` source フレームをスキップしない — enriched フレームは Figma 実値を保持（Issue 63）するため 4px 刻みでない場合がある。`source == 'exact'` のフレームをスキップするよう修正 |
| 112 | テスト | **FIXED** | `run-tests.sh` `assert_json_range`/`assert_json_gte`/cross-script テストのシェル変数 Python インジェクション — Issue 64/95 と同様の問題。`$actual`/`$min`/`$max` を `sys.argv` 経由に変更 |
| 113 | テスト | **FIXED** | `run-tests.sh` コメント「Phase 2 renames」が「Phase 3 renames」の誤り — テストメッセージ（line 497/501）は正しいがコメント（line 499）が古い Phase 番号のまま |
| 114 | docs | **FIXED** | `phase-details.md` 出力例の3箇所不整合 — (a) YAML に `max_section_depth` 欠落（Issue 71 追加分）、(b) コンソール ungrouped_penalty が -10.0 だが 5 候補 × 1 = -5.0 が正、(c) score 65 が実際のペナルティ合計 39.9 と不一致（60 に修正） |
| 115 | 4 | **FIXED** | `infer-autolayout.sh` YAML出力に `primary_axis_align` が欠落 — `apply-autolayout.js` が常に `MIN` をデフォルト適用してしまう。YAML書き出しループに `primary_axis_align` 行を追加 |
| 116 | 1 | **FIXED** | `is_section_root()` が FRAME 型のみ判定 — COMPONENT/INSTANCE/SECTION 型のセクションルートで `section_depth` がリセットされず深さスコアが不正に加算される。型チェックを拡張 |
| 117 | 2 | **FIXED** | `apply-grouping.js` 出力に `total` フィールドが欠落 — `apply-renames.js` と `apply-autolayout.js` は `total` を含むが `apply-grouping.js` のみ欠落。`total: groupingPlan.length` を追加 |
| 118 | 4 | **FIXED** | `infer-autolayout.sh` YAML出力のキー名 `counter_align` が `counter_axis_align` と不一致 — データ構造と `apply-autolayout.js` は `counter_axis_align` を期待。YAMLキーを `counter_axis_align` に統一 |
| 119 | 3 | **FIXED** | `clone-artboard.js` が FRAME 型のみサポート — `is_section_root()` は COMPONENT/INSTANCE/SECTION も有効だが clone 時に拒否される。型チェックを `ALLOWED_TYPES` 配列に拡張 |
| 120 | 2 | **FIXED** | `_split_by_spatial_gap` のマジックナンバー `gap_threshold=100` — 名前付き定数 `SPATIAL_GAP_THRESHOLD` に抽出。`figma-prepare.md` 閾値テーブルにも追加 |
| 121 | 2 | **FIXED** | `detect_vertical_zone_groups` の非対称オーバーラップ閾値（50%/30%）が未文書化 — `ZONE_OVERLAP_ITEM`/`ZONE_OVERLAP_ZONE` 定数に抽出、コメント追加、`figma-prepare.md` 閾値テーブルにも追加 |
| 122 | 4 | **FIXED** | `apply-autolayout.js` JSDoc 出力形式に `total` フィールドが欠落 — 実際の return は `total` を含む（Issue 117 で追加済み）が JSDoc が未更新。JSDoc を修正 |
| 123 | 2 | **FIXED** | `detect_header_footer_groups` のマジックナンバー（120px/300px）— `HEADER_ZONE_HEIGHT`/`FOOTER_ZONE_HEIGHT` 定数に抽出。`figma-prepare.md` 閾値テーブルにも追加 |
| 124 | 3 | **FIXED** | `generate-rename-map.sh` の多数のマジックナンバーを名前付き定数に抽出 — 14個の閾値定数（`DIVIDER_MAX_HEIGHT`, `HEADER_Y_THRESHOLD`, `FOOTER_PROXIMITY`, `FOOTER_MAX_HEIGHT`, `WIDE_ELEMENT_RATIO`, `WIDE_ELEMENT_MIN_WIDTH`, `ICON_MAX_SIZE`, `BUTTON_MAX_HEIGHT`, `BUTTON_MAX_WIDTH`, `BUTTON_TEXT_MAX_LEN`, `LABEL_MAX_LEN`, `NAV_MIN_TEXT_COUNT`, `NAV_MAX_TEXT_LEN`, `NAV_GRANDCHILD_MIN`）を追加。`figma-prepare.md` 閾値テーブルにも追加 |
| 125 | 2 | **FIXED** | `detect_header_footer_groups` の `bb['h'] < 200` マジックナンバー — `HEADER_MAX_ELEMENT_HEIGHT = 200` 定数に抽出 |
| 126 | 4 | **FIXED** | `infer-autolayout.sh` が INSTANCE/COMPONENT を推論するが `apply-autolayout.js` がスキップする不整合 — 出力に `applicable` フラグと `node_type` を追加。INSTANCE/COMPONENT は `applicable: false` で情報提供のみ |
| 127 | 2 | **FIXED** | proximity グループの `suggested_name` が Union-Find 内部インデックスを漏洩 — `group-proximity-{root}` を `group-{sequential_counter}` に変更 |
| 128 | 全体 | **FIXED** | `structure_hash()` が `detect-grouping-candidates.sh` 内にローカル定義され `figma_utils.py` の `structure_similarity()` と暗黙結合 — `figma_utils.py` に移動して明示的な依存関係に。public 関数カウント 18→19 |
| 129 | 2 | **FIXED** | `detect_header_footer_groups` のフッターゾーンに非対称な 50px マージンが未文書化 — `FOOTER_ZONE_MARGIN = 50` 定数に抽出、設計意図をコメントで明記 |
| 130 | テスト | **FIXED** | `run-tests.sh` に残存するシェル変数 Python インジェクション 8件 — `python3 -c "assert ...'$VAR'..."` パターンを全て `sys.argv` 経由に変更 |
| 131 | 全体 | **FIXED** | `row_tolerance=20` が4箇所に重複（共有定数なし）— `figma_utils.py` に `ROW_TOLERANCE = 20` 定数追加、全4箇所で参照 |
| 132 | 4 | **FIXED** | `layout_from_enrichment()` が WRAP レイアウトを未処理 — `layoutWrap == 'WRAP'` 時に direction を 'WRAP' に変換 |
| 133 | docs | **FIXED** | `analyze-structure.sh` コメントに陳腐な `(with 'xml' key)` 記述 — `(JSON with 'document' or 'node' key)` に更新 |
| 134 | 2 | **FIXED** | `detect_header_footer_groups` のヘッダー検証にマジックナンバー残存 — `HEADER_TEXT_MAX_WIDTH`, `HEADER_LOGO_MAX_WIDTH`, `HEADER_LOGO_MAX_HEIGHT`, `HEADER_NAV_MIN_TEXTS` 定数に抽出 |
| 135 | 2 | **FIXED** | `infer_zone_semantic_name` のマジックナンバー — `HERO_ZONE_DISTANCE`, `LARGE_BG_WIDTH_RATIO` 定数に抽出 |
| 136 | 全体 | **FIXED** | `compute_grouping_score` で `gap=0` 時に ZeroDivisionError — `gap <= 0` 時に早期リターン追加 |
| 137 | 1.5 | **FIXED** | `enrich-metadata.sh` の ENRICHMENT_KEYS に `layoutWrap` が欠落 — `'layoutWrap'` を追加 |
| 138 | 全体 | **FIXED** | `detect_regular_spacing()` の `0.25` がインラインマジックナンバー — Issue 101 の `CV_THRESHOLD` 定数抽出が未完了。`figma_utils.py` に `CV_THRESHOLD = 0.25` 追加 |
| 139 | テスト | **FIXED** | `run-tests.sh` line 812 のシェル変数インジェクション — `python3 -c "...open('$SEC_OUT')..."` を `sys.argv` 経由に変更（Issue 64/95/112/130 と同パターン） |
| 140 | 1 | **FIXED** | `FLAT_THRESHOLD`/`DEEP_NESTING_THRESHOLD` が `analyze-structure.sh` にローカル定義 — `figma_utils.py` に移動して共有定数化（`GRID_SNAP`/`ROW_TOLERANCE` と同様） |
| 141 | 2 | **FIXED** | `is_navigation_like` のマジックナンバー `200` — 同ファイル内の `HEADER_TEXT_MAX_WIDTH` 定数を参照するよう変更 |
| 142 | テスト | **FIXED** | `qa-check.sh` doc-staleness の grep パターン `"Stage A から削除済み"` が phase-details.md の実テキストと不一致 — `"Stage A から削除"` に修正し `"fills 依存"` を除外 |
| 143 | 4 | **FIXED** | `infer-autolayout.sh` YAML 出力に `node_type` フィールドが欠落 — JSON 出力との一貫性のため `node_type` 行を追加 |
| 144 | テスト | **FIXED** | `structure_hash()` の直接ユニットテスト未カバー — leaf/empty/missing type/sorted children/single/INSTANCE の6ケース追加（87件目） |
| 145 | 3 | **FIXED** | `collect_renames()` が `visible: false` ノードをスキップしない — 先頭に `visible == False` ガード追加 |
| 146 | 4 | **FIXED** | `walk_and_infer()` が SECTION 型ノードを除外 — 型チェックに `'SECTION'` 追加 |
| 147 | 全体 | **FIXED** | `detect_regular_spacing()` のデッドコード `mean_gap <= 0` — 正のgapフィルタ後は到達不能。削除 |
| 148 | 4 | **FIXED** | `infer-autolayout.sh` のマジックナンバー — `CENTER_ALIGN_VARIANCE = 4` / `ALIGN_TOLERANCE = 2` 定数化 |
| 149 | 2 | **FIXED** | `infer_zone_semantic_name()` hero 重複名リスク — `zone_counters['hero']` カウンタ使用に変更 |
| 150 | 4 | **FIXED** | `apply-autolayout.js` COMPONENT/SECTION 拒否の不整合 — `["FRAME","COMPONENT","SECTION"]` に拡張 |
| 151 | 2 | **FIXED** | `apply-grouping.js` `resize()` ゼロ寸法ガード — `Math.max(1, ...)` 追加 |
| 152 | 全体 | **FIXED** | `apply-*.js` 常に `success: true` — `applied > 0 \|\| errors.length === 0` に変更 |
| 153 | 3 | **FIXED** | `clone-artboard.js` 子要素数不一致の無警告切り詰め — `warnings` 配列追加、不一致時に警告出力 |
| 154 | テスト | **FIXED** | `helpers.sh` `$field` シェル変数インジェクション — SAFETY コメント追加（hardcoded literal 必須） |
| 155 | テスト | **FIXED** | ユニットテスト未カバー — `_raw_distance`(3件), `snap(grid=0/-1)`, `compute_grouping_score(gap=0)`, `is_section_root` COMPONENT/INSTANCE/SECTION 追加 |
| 156 | テスト | **FIXED** | Issue 32 テスト無条件 PASS — node `1:20` の enriched 出力にエラーがないことを実検証 |
| 157 | テスト | **FIXED** | `structure_hash` children+no-type テスト — `UNKNOWN:[TEXT,TEXT]` を期待。ソースも `'UNKNOWN'` デフォルトに修正 |
| 158 | docs | **FIXED** | `figma-prepare.md` ブランチ必須 → Adjacent Artboard 必須に更新 |
| 159 | docs | **FIXED** | `figma-prepare.md` グルーピングアルゴリズム — spacing/zone 手法追加、proximity をスコアリング方式に更新 |
| 160 | docs | **FIXED** | `figma-prepare.md` リネーム — sub-priority 3.1(Header/Footer)/3.2(Icon)/3.5(Nav) 追加 |
| 161 | docs | **FIXED** | `phase-details.md` Stage B fallback — 「Stage B スキップ、Stage A のみで進行」に統一 |
| 162 | docs | **FIXED** | `figma-prepare.md` Auto Layout — 2要素判定(dx vs dy)、WRAP検出、SPACE_BETWEEN 追加 |
| 163 | docs | **FIXED** | `figma-prepare.md` セマンティック検出 — Phase 2 Stage A の実手法(Card/Nav/Grid/Header/Footer)に更新 |
| 164 | docs | **FIXED** | `figma-prepare.md` 正規表現 — ケースインセンシティブの注記追加 |
| 165 | 2 | **FIXED** | Stage A: 連続パターン検出 — `detect_consecutive_similar()` を figma_utils.py + detect-grouping-candidates.sh に追加 |
| 166 | 2 | **FIXED** | Stage A: ヘッディング-コンテンツペア検出 — `is_heading_like()` + `detect_heading_content_pairs()` 追加 |
| 167 | 2 | **FIXED** | Stage A: 遊離要素吸収 — `find_absorbable_elements()` 後処理ステップ追加 |
| 168 | 2 | **FIXED** | Stage B: 階層的セクショニング — sectioning-prompt-template.md を階層出力 + subsections 対応に書き換え |
| 169 | 3 | **FIXED** | ラップ画像パターンのカード検出 — `has_image_wrapper()` を generate-rename-map.sh に追加 |
| 170 | 3 | **FIXED** | JP_KEYWORD_MAP 拡充 — ドメイン固有用語の追加（継続拡充中） |
| 171 | 3 | **FIXED** | カード項目 `heading-content` → `card-*` — RECTANGLE をカード画像として検出 + 幅1400px ガード + `_resolve_slug` でJPスラグ改善 |
| 172 | 3 | **FIXED** | `content-content` → `body-*` — TEXT-only フレームに `body-` プレフィックス + JP_KEYWORD_MAP 55語に拡充 + `_jp_keyword_lookup` 最長一致 |
| 173 | 2 | **FIXED** | 遊離LINE吸収を2パス化 — `_compute_zone_bboxes` でゾーンbbox計算 + Y中心がゾーン内なら distance=0 で吸収 |
| 174 | 3 | **FIXED** | `group-N`/`container-N` セマンティック命名 — 子/孫テキストから `_resolve_slug` + JP_KEYWORD_MAP でスラグ導出（例: `group-service`, `container-catering`） |
| 175 | 3 | **FIXED** | ELLIPSE 装飾 `is_heading_like` 誤検出排除 — `ELLIPSE > TEXT` のフレームを早期リターンで除外。装飾ドットパターン(3 ELLIPSE)が heading 扱いされなくなった |
| 176 | 2 | **FIXED** | Stage B subsections ラッパーが未適用 — SKILL.md に 2-4a〜2-4e の再帰的適用手順を追加 |
| 177 | 全体 | **FIXED** | `get_root_node` REST API 形式（`nodes.{id}.document`）未対応 — `nodes` キー検出ロジック追加 |
| 178 | 2 | **FIXED** | Stage A ルートレベル候補が Stage B と競合 — `--skip-root` フラグ追加 |
| 179 | 2 | **FIXED** | フラット構造でヘッダークラスター未検出 — `header_cluster_ids` ヒント追加 |
| 180 | 2 | **FIXED** | 背景レイヤー+コンテンツレイヤーのグルーピング未検出 — `detect_bg_content_layers()` 追加 |
| 181 | 2 | **FIXED** | テーブル行構造のグルーピング未検出 — `detect_table_rows()` 追加 |
| 182 | 1,2 | **FIXED** | ビューポート外要素（off-canvas）のフィルタリング — `is_off_canvas()` + `OFF_CANVAS_MARGIN` 追加 |
| 183 | 2 | **FIXED** | 親幅超過要素（oversized elements）のグルーピング誤分類 — `OVERFLOW_BG_MIN_WIDTH` + x<0 検出追加 |
| 184 | 2 | **FIXED** | ニュースバー（横並び多要素フラットパターン）— `detect_horizontal_bar()` 追加 |
| 185 | 3 | **FIXED** | 英語ラベル + 日本語見出しペアのリネーム — `detect_en_jp_label_pairs()` 追加 |
| 186 | 2 | **FIXED** | ブログカード（分離型カードパターン）— `detect_repeating_tuple()` 追加 |
| 187 | 1 | **FIXED** | hidden 要素のスコアリング除外 — `count_nodes()` に visible ガード追加 |
| 188 | 1 | **FIXED** | 超フラット構造（85+直接子要素）のスコア精度検証 — flat_penalty 上限 30→40 + `named_rate_pct` 追加 |
| 189 | 2,3 | **FIXED** | 装飾ドットパターン — `is_decoration_pattern()` + Priority 4.0 追加 |
| 190 | 2,3 | **FIXED** | ハイライトテキスト — `detect_highlight_text()` + method='highlight' 追加 |
| 191 | 2 | **FIXED** | フッター統合ラッパー（幅超過 Group）— `is_section_root()` 幅判定緩和（`width >= 1296px`） |
| 192 | 3 | **FIXED** | SNS/サイドパネル — Priority 3.16 サイドパネル検出追加 |
| 193 | 3 | **FIXED** | CTA ボタン — Priority 3.15 CTA 検出追加 |
| 194 | 2(arch) | **OPEN** | Phase B Claude推論のネストレベル拡張 — Stage A 検出器の段階的置換 |
| 195 | 1 | **FIXED** | `analyze-structure.sh` インラインPython内の未エスケープダブルクオート — コメント内の `"..."` が bash の文字列終端と解釈され SyntaxError |
| 196 | 2,3 | **FIXED** | マジックナンバー定数化漏れ（horizontal_bar variance_ratio=3, highlight x_overlap=0.5）— `HORIZONTAL_BAR_VARIANCE_RATIO`, `HIGHLIGHT_X_OVERLAP_RATIO` 追加 + figma-prepare.md 閾値テーブル更新 |
| 197 | 2 | **FIXED** | `detect_heading_content_pairs` マジックナンバー 0.8 — `HEADING_SOFT_HEIGHT_RATIO` 定数化 + figma-prepare.md 追加 |
| 198 | 2 | **FIXED** | `walk_and_detect` で `get_bbox(node)` 二重呼び出し — `page_bb_pre` 再利用に修正 |
| 199 | 全体 | **FIXED** | `_compute_child_types` TYPE_ABBR に IMAGE 欠落 — 'IMG' 追加。IMAGE ノードが 'OTH' に誤分類されていた |
| 200 | 3 | **FIXED** | `generate-rename-map.sh` マジックナンバー `w < 1400` — `OVERFLOW_BG_MIN_WIDTH` 定数参照に修正 |
| 201 | 2(B) | **OPEN** | `prepare-sectioning-context.sh` ヘッダー/フッター検出に複数マジックナンバー — `page_h * 0.05`, `page_h * 0.9`, `page_w * 0.8`, 背景 `bb['h'] >= 100`, ヘッディング `child_h > 200`, 遊離 `bb['h'] <= 20` が Stage B ヒント関数内にハードコード |
| 202 | 4 | **OPEN** | `infer-autolayout.sh` の `CENTER_ALIGN_VARIANCE=4` / `ALIGN_TOLERANCE=2` が figma-prepare.md 閾値テーブルに未登録 — Issue 148 で定数化済みだがドキュメント未反映 |
| 203 | 全体 | **OPEN** | `_compute_flags` 内マジックナンバー — `1.05`（overflow判定5%許容）、`1.02`（overflow-y 2%許容）、`0.95`（bg-full判定）、`50`（tiny判定）がハードコード |
| 204 | 2 | **OPEN** | `detect_bg_content_layers` left-overflow 判定の `parent_bb['w'] * 0.5` が figma-prepare.md 閾値テーブルに未登録 |
| 205 | 2 | **OPEN** | `detect_heading_content_pairs` ロジックの設計意図不明瞭 — 40-80% 中間ゾーンが意図的か不明。コメントに設計意図を明記すべき |
| 206 | 2 | **OPEN** | `_split_by_spatial_gap` 非リーフ6要素の閾値がハードコード — `len(nodes) < 6` の `6` が figma-prepare.md 未登録 |
| 207 | テスト | **FIXED** | run-tests.sh `$SEMANTIC_FIXTURE` シェル変数インジェクション — `sys.argv[1]` パターンに修正 |
| 208 | テスト | **FIXED** | `_compute_zone_bboxes` 直接ユニットテスト追加（5テスト） |
| 209 | テスト | **FIXED** | `detect_horizontal_bar` エッジケーステスト追加（6テスト） |
| 210 | テスト | **FIXED** | `detect_bg_content_layers` ELLIPSE装飾/コンテンツ境界値テスト追加（2テスト） |
| 211 | テスト | **FIXED** | `detect_repeating_tuple` single distinct type スキップテスト追加（2テスト） |
| 212 | テスト | **FIXED** | qa-check.sh に detector-coverage チェック（カテゴリ6）追加 |
| 213 | テスト | **FIXED** | `generate_enriched_table` overflow_y エッジケーステスト追加（3テスト） |
