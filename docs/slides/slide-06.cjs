function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u7528\u6237\u4F53\u9A8C\u4F18\u5316", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Quick actions section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 2.2,
    fill: { color: theme.primary }
  });

  slide.addText("\u5FEB\u6377\u64CD\u4F5C", {
    x: 0.7, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "Ctrl + K  \u5168\u5C40\u641C\u7D22", options: { breakLine: true } },
    { text: "Ctrl + 1~9  \u5FEB\u901F\u5BFC\u822A", options: { breakLine: true } },
    { text: "\u5FEB\u901F\u547D\u4EE4\u9762\u677F  \u6253\u5F00\u5E38\u7528\u64CD\u4F5C" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 1.4,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // User guidance section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 2.2,
    fill: { color: theme.primary }
  });

  slide.addText("\u7528\u6237\u5F15\u5BFC", {
    x: 5.4, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2605 \u65B0\u624B\u5F15\u5BFC\u6559\u7A0B", options: { breakLine: true } },
    { text: "   \u6B63\u786E\u5F15\u5BFC\u65B0\u7528\u6237\u4E86\u89E3\u7CFB\u7EDF\u529F\u80FD", options: { breakLine: true } },
    { text: "\u2605 \u529F\u80FD\u63D0\u793A", options: { breakLine: true } },
    { text: "   \u9F20\u6807\u60AC\u505C\u663E\u793A\u8BE6\u7EC6\u4FE1\u606F", options: { breakLine: true } },
    { text: "\u2605 \u5E2E\u52A9\u6587\u6863", options: { breakLine: true } },
    { text: "   \u7CFB\u7EDF\u7684\u5E2E\u52A9\u9875\u9762\u63D0\u4F9B\u5FEB\u901F\u67E5\u8BE2" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 1.4,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Bottom highlight - UX benefits
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.9, w: 9, h: 1.4,
    fill: { color: theme.secondary }
  });

  slide.addText("\u7528\u6237\u4F53\u9A8C\u4F18\u5316\u7684\u4EFB\u52A1", {
    x: 0.7, y: 4.0, w: 8.5, h: 0.5,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText("\u201C\u5C06\u590D\u6742\u64CD\u4F5C\u7F29\u77ED\u4E3A\u51E0\u6B21\u70B9\u51FB\uFF0C\u901A\u8FC7\u667A\u80FD\u63D0\u793A\u5C06\u4F53\u9A8C\u98CE\u9669\u964D\u4F4E\u81F3\u6700\u4F4E\u201D", {
    x: 0.7, y: 4.5, w: 8.5, h: 0.7,
    fontSize: 14, fontFace: "Microsoft YaHei", italic: true,
    color: theme.light, align: "left", valign: "top"
  });

  // Page number
  slide.addText("06", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };