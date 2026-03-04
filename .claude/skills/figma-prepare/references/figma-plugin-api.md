# Figma Plugin API Patterns

## Overview

Chrome DevTools MCP の `evaluate_script` で使用する Figma Plugin API パターン集。
Phase 2-4 のスクリプト生成時に参照する。

**全コード例は `() => { ... }` アロー関数形式**。
`mcp__chrome-devtools__evaluate_script` の `function` パラメータにそのまま渡せる。

## 基本操作

### ノード取得

```javascript
() => {
  // ID でノード取得
  const node = figma.getNodeById("1:10");

  // 現在のページ
  const page = figma.currentPage;

  // ページ内の全子要素
  return page.children.map(c => ({ id: c.id, name: c.name, type: c.type }));
}
```

### ノードプロパティ

```javascript
() => {
  const node = figma.getNodeById("1:10");
  if (!node) return { error: "not found" };

  return {
    name: node.name,
    type: node.type,    // "FRAME", "TEXT", "RECTANGLE", etc.
    x: node.x,
    y: node.y,
    width: node.width,
    height: node.height,
    parentId: node.parent?.id,
    childCount: "children" in node ? node.children.length : 0,
  };
}
```

## Adjacent Artboard（複製 + IDマッピング）

### アートボード複製

```javascript
() => {
  const sourceNodeId = "1:4";  // 複製元のアートボードID
  const GAP = 100;             // 元と複製の間隔 (px)

  const source = figma.getNodeById(sourceNodeId);
  if (!source || source.type !== "FRAME") {
    return { success: false, error: "not a frame or not found" };
  }

  // 深い複製（全子要素を含む）
  const clone = source.clone();
  clone.name = `${source.name} [prepared]`;
  clone.x = source.x + source.width + GAP;
  clone.y = source.y;
  figma.currentPage.appendChild(clone);

  return {
    success: true,
    clone: { id: clone.id, name: clone.name, x: clone.x, y: clone.y },
  };
}
```

### IDマッピングテーブル生成

`clone()` は子要素の順序を保持するため、インデックスベースの並行DFS走査で正確にマッピングできる。

```javascript
() => {
  const originalId = "1:4";
  const cloneId = "2:100";  // clone() の戻り値から取得

  const mapping = {};
  let total = 0;
  let nameMatches = 0;

  function buildMapping(origNode, cloneNode) {
    mapping[origNode.id] = cloneNode.id;
    total++;
    if (origNode.name === cloneNode.name) nameMatches++;

    if ("children" in origNode && "children" in cloneNode) {
      const len = Math.min(origNode.children.length, cloneNode.children.length);
      for (let i = 0; i < len; i++) {
        buildMapping(origNode.children[i], cloneNode.children[i]);
      }
    }
  }

  const orig = figma.getNodeById(originalId);
  const clone = figma.getNodeById(cloneId);
  buildMapping(orig, clone);

  return {
    mapping,
    total,
    nameMatchRate: total > 0 ? nameMatches / total : 0,
  };
}
```

**注意**: `nameMatchRate` が 95% 未満の場合、マッピングが不正確な可能性あり。

## Phase 2: リネーム

### 一括リネーム

```javascript
() => {
  const renameMap = {
    "1:10": "hero-background",
    "1:11": "hero-title",
    "1:12": "hero-description",
  };

  let renamed = 0;
  const errors = [];

  for (const [nodeId, newName] of Object.entries(renameMap)) {
    try {
      const node = figma.getNodeById(nodeId);
      if (node) {
        node.name = newName;
        renamed++;
      } else {
        errors.push({ nodeId, error: "not found" });
      }
    } catch (e) {
      errors.push({ nodeId, error: e.message });
    }
  }

  return { renamed, errors, total: Object.keys(renameMap).length };
}
```

### バッチ実行（50件/回）

```javascript
() => {
  // バッチ N of M
  const batch = {/* 50件分のrenameMap */};
  let renamed = 0;

  for (const [nodeId, newName] of Object.entries(batch)) {
    const node = figma.getNodeById(nodeId);
    if (node) { node.name = newName; renamed++; }
  }

  return { renamed, batch: "N/M" };
}
```

## Phase 3: グループ化

### Frame でグループ化

```javascript
() => {
  const group = {
    parentId: "1:5",
    childIds: ["1:10", "1:11", "1:12"],
    name: "card-feature",
  };

  const parent = figma.getNodeById(group.parentId);
  if (!parent) return { error: "parent not found" };

  const children = group.childIds
    .map(id => figma.getNodeById(id))
    .filter(Boolean);

  if (children.length === 0) return { error: "no children found" };

  // 子要素の境界を計算
  const minX = Math.min(...children.map(c => c.x));
  const minY = Math.min(...children.map(c => c.y));
  const maxX = Math.max(...children.map(c => c.x + c.width));
  const maxY = Math.max(...children.map(c => c.y + c.height));

  // 新しい Frame を作成
  const frame = figma.createFrame();
  frame.name = group.name;
  frame.x = minX;
  frame.y = minY;
  frame.resize(maxX - minX, maxY - minY);
  frame.fills = []; // 透明

  // 親に追加してから子要素を移動
  parent.appendChild(frame);
  for (const child of children) {
    child.x -= minX;
    child.y -= minY;
    frame.appendChild(child);
  }

  return { created: frame.id, name: frame.name, children: children.length };
}
```

## Phase 4: Auto Layout

### Auto Layout 適用

```javascript
() => {
  const settings = {
    nodeId: "1:20",
    direction: "VERTICAL",   // "HORIZONTAL" | "VERTICAL"
    gap: 16,
    padding: { top: 24, right: 24, bottom: 24, left: 24 },
    primaryAlign: "MIN",     // "MIN" | "CENTER" | "MAX" | "SPACE_BETWEEN"
    counterAlign: "CENTER",  // "MIN" | "CENTER" | "MAX"
  };

  const node = figma.getNodeById(settings.nodeId);
  if (!node || node.type !== "FRAME") {
    return { error: "not a frame or not found" };
  }

  node.layoutMode = settings.direction;
  node.itemSpacing = settings.gap;
  node.paddingTop = settings.padding.top;
  node.paddingRight = settings.padding.right;
  node.paddingBottom = settings.padding.bottom;
  node.paddingLeft = settings.padding.left;
  node.primaryAxisAlignItems = settings.primaryAlign;
  node.counterAxisAlignItems = settings.counterAlign;
  node.primaryAxisSizingMode = "AUTO";
  node.counterAxisSizingMode = "AUTO";

  return {
    applied: node.id,
    name: node.name,
    layout: settings.direction,
    gap: settings.gap,
  };
}
```

### 一括 Auto Layout

```javascript
() => {
  const frames = [
    { nodeId: "1:20", direction: "VERTICAL", gap: 16, padding: [24, 24, 24, 24] },
    { nodeId: "1:30", direction: "HORIZONTAL", gap: 12, padding: [0, 0, 0, 0] },
  ];

  let applied = 0;
  const errors = [];

  for (const f of frames) {
    try {
      const node = figma.getNodeById(f.nodeId);
      if (!node || node.type !== "FRAME") {
        errors.push({ nodeId: f.nodeId, error: "not a frame" });
        continue;
      }

      node.layoutMode = f.direction;
      node.itemSpacing = f.gap;
      node.paddingTop = f.padding[0];
      node.paddingRight = f.padding[1];
      node.paddingBottom = f.padding[2];
      node.paddingLeft = f.padding[3];
      node.primaryAxisSizingMode = "AUTO";
      node.counterAxisSizingMode = "AUTO";

      applied++;
    } catch (e) {
      errors.push({ nodeId: f.nodeId, error: e.message });
    }
  }

  return { applied, errors, total: frames.length };
}
```

## 構造検証

### ツリー読み戻し + 名前一致検証

`apply-renames.js` や Phase 3 グルーピング後に、クローンのツリーを読み戻して期待名と比較する。

```javascript
() => {
  const cloneNodeId = "23:128";   // クローンアートボードのID
  const expectedNames = {         // クローン側nodeId → 期待名
    "23:130": "hero-background",
    "23:131": "hero-title",
    "23:132": "hero-description",
  };

  const cloneRoot = figma.getNodeById(cloneNodeId);
  if (!cloneRoot) return { success: false, error: "clone not found" };

  // DFS でクローン内の全ノードIDを収集
  const cloneNodeIds = new Set();
  function collectIds(node) {
    cloneNodeIds.add(node.id);
    if ("children" in node) {
      for (const child of node.children) collectIds(child);
    }
  }
  collectIds(cloneRoot);

  // 期待名と実名を比較
  let matched = 0;
  const mismatched = [];
  const missing = [];

  for (const [nodeId, expectedName] of Object.entries(expectedNames)) {
    if (!cloneNodeIds.has(nodeId)) { missing.push(nodeId); continue; }
    const node = figma.getNodeById(nodeId);
    if (!node) { missing.push(nodeId); continue; }
    if (node.name === expectedName) { matched++; }
    else { mismatched.push({ nodeId, expected: expectedName, actual: node.name }); }
  }

  const total = Object.keys(expectedNames).length;
  return {
    success: true,
    total,
    matched,
    mismatched,
    missing,
    matchRate: total > 0 ? matched / total : 0,
  };
}
```

**判定基準**: `matchRate >= 0.98` → 成功、`< 0.98` → 警告 + mismatch 一覧

**用途**:
- Phase 2: リネーム後の名前一致検証（primary）
- Phase 3: グルーピング後のフレーム名・子構造検証

**テンプレート**: `scripts/verify-structure.js` にプレースホルダー版あり

## ユーティリティ

### 存在チェック

```javascript
() => {
  const ids = ["1:10", "1:11", "1:12"];
  const found = [];
  const missing = [];

  for (const id of ids) {
    const node = figma.getNodeById(id);
    if (node) { found.push(id); } else { missing.push(id); }
  }

  return { found: found.length, missing };
}
```

### ページ情報取得

```javascript
() => {
  const page = figma.currentPage;
  return {
    name: page.name,
    childCount: page.children.length,
    children: page.children.map(c => ({
      id: c.id,
      name: c.name,
      type: c.type,
      x: c.x,
      y: c.y,
      width: c.width,
      height: c.height,
    })),
  };
}
```

### 複製アートボード削除

```javascript
() => {
  const cloneId = "23:128";
  const clone = figma.getNodeById(cloneId);
  if (!clone) return { error: "not found" };
  clone.remove();
  return { success: true, removed: cloneId };
}
```

## 制限事項

| 制限 | 詳細 |
|------|------|
| 実行コンテキスト | Plugin sandbox 内（DOM アクセス不可） |
| 非同期制限 | `await` は使用可能だが、外部 fetch は不可 |
| タイムアウト | 長時間実行は避ける（バッチ分割で対処） |
| 読み取り専用プロパティ | `id`, `type`, `parent` 等は変更不可 |
| コンポーネント制約 | Instance の detach は禁止（ルール参照） |
| 戻り値 | MCP が自動シリアライズ。`JSON.stringify()` 不要 |
