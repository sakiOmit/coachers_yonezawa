# Figma Plugin API Patterns

## Overview

Chrome DevTools MCP の `evaluate_script` で使用する Figma Plugin API パターン集。
Phase 2-4 のスクリプト生成時に参照する。

## 基本操作

### ノード取得

```javascript
// ID でノード取得
const node = figma.getNodeById("1:10");

// 現在のページ
const page = figma.currentPage;

// ページ内の全子要素
const children = figma.currentPage.children;
```

### ノードプロパティ

```javascript
// 名前変更
node.name = "new-name";

// タイプ確認
node.type; // "FRAME", "TEXT", "RECTANGLE", etc.

// 位置・サイズ
node.x;
node.y;
node.width;
node.height;

// 親ノード
node.parent;

// 子ノード（FRAME, GROUP等）
node.children;
```

## Phase 2: リネーム

### 一括リネーム

```javascript
(async () => {
  const renameMap = {
    "1:10": "hero-background",
    "1:11": "hero-title",
    "1:12": "hero-description",
  };

  let renamed = 0;
  let errors = [];

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

  return JSON.stringify({ renamed, errors, total: Object.keys(renameMap).length });
})();
```

### バッチ実行（50件/回）

```javascript
(async () => {
  // バッチ N of M
  const batch = {/* 50件分のrenameMap */};
  let renamed = 0;

  for (const [nodeId, newName] of Object.entries(batch)) {
    const node = figma.getNodeById(nodeId);
    if (node) { node.name = newName; renamed++; }
  }

  return JSON.stringify({ renamed, batch: "N/M" });
})();
```

## Phase 3: グループ化

### Frame でグループ化

```javascript
(async () => {
  const group = {
    parentId: "1:5",
    childIds: ["1:10", "1:11", "1:12"],
    name: "card-feature",
  };

  const parent = figma.getNodeById(group.parentId);
  if (!parent) return JSON.stringify({ error: "parent not found" });

  const children = group.childIds
    .map(id => figma.getNodeById(id))
    .filter(Boolean);

  if (children.length === 0) return JSON.stringify({ error: "no children found" });

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

  return JSON.stringify({ created: frame.id, name: frame.name, children: children.length });
})();
```

## Phase 4: Auto Layout

### Auto Layout 適用

```javascript
(async () => {
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
    return JSON.stringify({ error: "not a frame or not found" });
  }

  // Auto Layout を適用
  node.layoutMode = settings.direction;
  node.itemSpacing = settings.gap;
  node.paddingTop = settings.padding.top;
  node.paddingRight = settings.padding.right;
  node.paddingBottom = settings.padding.bottom;
  node.paddingLeft = settings.padding.left;
  node.primaryAxisAlignItems = settings.primaryAlign;
  node.counterAxisAlignItems = settings.counterAlign;

  // サイズモード
  node.primaryAxisSizingMode = "AUTO";
  node.counterAxisSizingMode = "AUTO";

  return JSON.stringify({
    applied: node.id,
    name: node.name,
    layout: settings.direction,
    gap: settings.gap,
  });
})();
```

### 一括 Auto Layout

```javascript
(async () => {
  const frames = [
    { nodeId: "1:20", direction: "VERTICAL", gap: 16, padding: [24, 24, 24, 24] },
    { nodeId: "1:30", direction: "HORIZONTAL", gap: 12, padding: [0, 0, 0, 0] },
  ];

  let applied = 0;
  let errors = [];

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

  return JSON.stringify({ applied, errors, total: frames.length });
})();
```

## ユーティリティ

### 存在チェック

```javascript
// 実行前に全 nodeId の存在を確認
(async () => {
  const ids = ["1:10", "1:11", "1:12"];
  const found = [];
  const missing = [];

  for (const id of ids) {
    const node = figma.getNodeById(id);
    if (node) { found.push(id); } else { missing.push(id); }
  }

  return JSON.stringify({ found: found.length, missing });
})();
```

### ページ情報取得

```javascript
(async () => {
  const page = figma.currentPage;
  return JSON.stringify({
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
  });
})();
```

## 制限事項

| 制限 | 詳細 |
|------|------|
| 実行コンテキスト | Plugin sandbox 内（DOM アクセス不可） |
| 非同期制限 | `await` は使用可能だが、外部 fetch は不可 |
| タイムアウト | 長時間実行は避ける（バッチ分割で対処） |
| 読み取り専用プロパティ | `id`, `type`, `parent` 等は変更不可 |
| コンポーネント制約 | Instance の detach は禁止（ルール参照） |
