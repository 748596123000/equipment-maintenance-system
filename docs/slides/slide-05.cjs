function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u6838\u5FC3\u529F\u80FD \u4E0B", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Feature 3: Standardized Work Guide
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 3.8,
    fill: { color: theme.primary }
  });

  // Feature 3 number badge
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: theme.accent }
  });
  slide.addText("3", {
    x: 0.5, y: 1.4, w: 0.5, h: 0.5,
    fontSize: 20, fontFace: "Arial", bold: true,
    color: theme.bg, align: "center", valign: "middle"
  });

  slide.addText("\u6807\u51C6\u5316\u4F5C\u4E1A\u6307\u5F15", {
    x: 1.1, y: 1.5, w: 3.5, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2605 AI\u751F\u6210\u4F5C\u4E1A\u6307\u5F15\u4E66", options: { breakLine: true } },
    { text: "   \u57FA\u4E8E\u68C0\u7D22\u7ED3\u679C\u81EA\u52A8\u751F\u6210\u68C0\u4FEE\u6B65\u9AA4\u6307\u5F15", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u591A\u5B89\u5168\u7B49\u7EA7\u914D\u7F6E", options: { breakLine: true } },
    { text: "   \u652F\u6301\u521D\u7EA7/\u4E2D\u7EA7/\u9AD8\u7EA7\u68C0\u4FEE\u4EBA\u5458\u914D\u7F6E", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 Word\u683C\u5F0F\u5BFC\u51FA", options: { breakLine: true } },
    { text: "   \u4E00\u952E\u5BFC\u51FAWord\u6587\u6863\uFF0C\u65B9\u4FBF\u6253\u5370\u4E0E\u5206\u4EAB", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u5386\u53F2\u6307\u5F15\u590D\u7528", options: { breakLine: true } },
    { text: "   \u5F52\u7C7B\u6848\u4F8B\u8BB0\u5F55\uFF0C\u5FEB\u901F\u91CD\u590D\u5F15\u7528" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 3,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Feature 4: Knowledge Management
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 3.8,
    fill: { color: theme.primary }
  });

  // Feature 4 number badge
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: theme.accent }
  });
  slide.addText("4", {
    x: 5.2, y: 1.4, w: 0.5, h: 0.5,
    fontSize: 20, fontFace: "Arial", bold: true,
    color: theme.bg, align: "center", valign: "middle"
  });

  slide.addText("\u77E5\u8BC6\u6C89\u6DC0\u4E0E\u66F4\u65B0", {
    x: 5.8, y: 1.5, w: 3.5, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2605 \u6587\u6863\u4E0A\u4F20\u4E0E\u5BA1\u6838", options: { breakLine: true } },
    { text: "   \u652F\u6301\u591A\u79CD\u683C\u5F0F\u4E0A\u4F20\uFF0C\u7BA1\u7406\u5458\u5BA1\u6838\u540E\u5165\u5E93", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u6848\u4F8B\u7BA1\u7406", options: { breakLine: true } },
    { text: "   \u6807\u8BB0\u91CD\u8981\u6848\u4F8B\uFF0C\u5EFA\u7ACB\u9891\u5927\u6848\u4F8B\u5E93", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u77E5\u8BC6\u56FE\u8C31\u53EF\u89C6\u5316", options: { breakLine: true } },
    { text: "   \u56FE\u5F62\u5316\u5C55\u793A\u77E5\u8BC6\u5173\u7CFB\uFF0C\u6613\u4E8E\u7406\u89E3\u4E0E\u5206\u6790", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u6301\u7EED\u66F4\u65B0\u673A\u5236", options: { breakLine: true } },
    { text: "   \u5B9A\u671F\u66F4\u65B0\u77E5\u8BC6\u5E93\uFF0C\u4FDD\u8BC1\u5185\u5BB9\u65F6\u6548\u6027" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 3,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Page number
  slide.addText("05", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };