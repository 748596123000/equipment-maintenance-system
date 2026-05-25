function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u5B9E\u65F6\u901A\u77E5\u7CFB\u7EDF", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Two-way notification flow
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 9, h: 1.2,
    fill: { color: theme.primary }
  });

  slide.addText("\u53CC\u5411\u901A\u77E5\u6D41", {
    x: 0.7, y: 1.5, w: 4, h: 0.4,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", margin: 0
  });

  // Flow arrows
  slide.addText("\u7528\u6237\u4E0A\u4F20  \u2192  \u7BA1\u7406\u5458\u5BA1\u6838  \u2192  \u7528\u6237\u63A5\u6536", {
    x: 0.7, y: 1.95, w: 8.5, h: 0.5,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Notification methods - 3 cards
  const cardW = 2.8;
  const cardH = 1.8;
  const cardY = 2.8;

  // Card 1: In-app messages
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: cardY, w: cardW, h: cardH,
    fill: { color: theme.secondary }
  });
  slide.addText("\u7AD9\u5185\u6D88\u606F", {
    x: 0.5, y: cardY + 0.1, w: cardW, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });
  slide.addText("\u6D88\u606F\u4E0B\u62C9\u83DC\u5355\n\u5373\u65F6\u67E5\u770B\u65B0\u901A\u77E5", {
    x: 0.6, y: cardY + 0.6, w: cardW - 0.2, h: 1.1,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Card 2: Sound alerts
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3.6, y: cardY, w: cardW, h: cardH,
    fill: { color: theme.secondary }
  });
  slide.addText("\u58F0\u97F3\u63D0\u793A", {
    x: 3.6, y: cardY + 0.1, w: cardW, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });
  slide.addText("\u65B0\u901A\u77E5\u5230\u8FBE\u65F6\n\u81EA\u52A8\u5531\u97F3\u63D0\u793A", {
    x: 3.7, y: cardY + 0.6, w: cardW - 0.2, h: 1.1,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Card 3: Desktop notification
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 6.7, y: cardY, w: cardW, h: cardH,
    fill: { color: theme.secondary }
  });
  slide.addText("\u684C\u9762\u901A\u77E5", {
    x: 6.7, y: cardY + 0.1, w: cardW, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });
  slide.addText("\u6D4F\u89C8\u5668\u684C\u9762\u63A8\u9001\n\u65E0\u9700\u6253\u5F00\u7CFB\u7EDF", {
    x: 6.8, y: cardY + 0.6, w: cardW - 0.2, h: 1.1,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Persistence section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.8, w: 9, h: 0.5,
    fill: { color: theme.primary }
  });
  slide.addText("\u901A\u77E5\u6301\u4E45\u5316  |  \u6570\u636E\u5E93\u5B58\u50A8  |  \u672A\u8BFB\u8BA1\u6570\u7EDF\u60C5\u6001", {
    x: 0.5, y: 4.8, w: 9, h: 0.5,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("07", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };