function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u6280\u672F\u67B6\u6784", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Architecture diagram area - center
  const boxY = 1.5;
  const boxH = 0.7;

  // Layer 1: Frontend
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: boxY, w: 9, h: boxH,
    fill: { color: theme.accent, transparency: 20 },
    line: { color: theme.accent, width: 2 }
  });
  slide.addText("  [ Frontend ]  React 18 + Vite + Tailwind CSS + Zustand + React Router 7  |  PC & Mobile \u54CD\u5E94\u5F0F\u8BBE\u8BA1", {
    x: 0.5, y: boxY, w: 9, h: boxH,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "middle"
  });

  // Arrow down
  slide.addText("\u25BC", {
    x: 4.5, y: boxY + boxH, w: 1, h: 0.4,
    fontSize: 20, fontFace: "Arial",
    color: theme.accent, align: "center"
  });

  // Layer 2: API Gateway
  const layer2Y = boxY + boxH + 0.4;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: layer2Y, w: 9, h: boxH,
    fill: { color: theme.secondary },
    line: { color: theme.accent, width: 2 }
  });
  slide.addText("  [ API Layer ]  FastAPI + Python  |  RESTful API + JWT Auth + CORS", {
    x: 0.5, y: layer2Y, w: 9, h: boxH,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "middle"
  });

  // Arrow down
  slide.addText("\u25BC", {
    x: 4.5, y: layer2Y + boxH, w: 1, h: 0.4,
    fontSize: 20, fontFace: "Arial",
    color: theme.accent, align: "center"
  });

  // Layer 3: AI + Data
  const layer3Y = layer2Y + boxH + 0.4;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: layer3Y, w: 4.3, h: boxH,
    fill: { color: theme.primary },
    line: { color: theme.accent, width: 1 }
  });
  slide.addText("  [ AI Model ]  \u901A\u4E49\u5343\u95EE  ( Qwen )", {
    x: 0.5, y: layer3Y, w: 4.3, h: boxH,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.accent, align: "left", valign: "middle"
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: layer3Y, w: 4.3, h: boxH,
    fill: { color: theme.primary },
    line: { color: theme.accent, width: 1 }
  });
  slide.addText("  [ Vector DB ]  ChromaDB", {
    x: 5.2, y: layer3Y, w: 4.3, h: boxH,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.accent, align: "left", valign: "middle"
  });

  // Arrow down
  slide.addText("\u25BC", {
    x: 4.5, y: layer3Y + boxH, w: 1, h: 0.4,
    fontSize: 20, fontFace: "Arial",
    color: theme.accent, align: "center"
  });

  // Layer 4: Database
  const layer4Y = layer3Y + boxH + 0.4;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: layer4Y, w: 9, h: boxH,
    fill: { color: theme.primary },
    line: { color: theme.accent, width: 1 }
  });
  slide.addText("  [ Data Layer ]  SQLite  |  \u6587\u6863\u7BA1\u7406 + \u7528\u6237\u7BA1\u7406 + \u77E5\u8BC6\u5E93", {
    x: 0.5, y: layer4Y, w: 9, h: boxH,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.accent, align: "left", valign: "middle"
  });

  // Footer: Deployment
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.8, w: 9, h: 0.5,
    fill: { color: theme.secondary }
  });
  slide.addText("[ Deployment ]  Docker\u5BB9\u5668\u5316\u90E8\u7F72  |  \u652F\u6301\u9F99\u82AFLoongArch + \u94F6\u6CB3\u9B81\u9F99\u64CD\u4F5C\u7CFB\u7EDF", {
    x: 0.5, y: 4.8, w: 9, h: 0.5,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("03", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };