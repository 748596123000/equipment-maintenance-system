function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u603B\u7ED3\u4E0E\u5C55\u671B", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Project achievements
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 2.3,
    fill: { color: theme.primary }
  });

  slide.addText("\u9879\u76EE\u6210\u679C", {
    x: 0.7, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2713 \u529F\u80FD\u5B8C\u6574\u5EA6\u9AD8", options: { breakLine: true } },
    { text: "   \u5B8C\u6210\u4E86\u68C0\u7D22\u3001\u95EE\u7B54\u3001\u6307\u5F15\u3001\u7BA1\u7406\u5168\u6D41\u7A0B", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2713 \u7528\u6237\u4F53\u9A8C\u4F18\u79C3", options: { breakLine: true } },
    { text: "   \u54CD\u5E94\u5F0F\u8BBE\u8BA1\u3001\u5FEB\u6377\u952E\u3001\u5F15\u5BFC\u6559\u7A0B", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2713 \u6280\u672F\u67B6\u6784\u5148\u8FDB", options: { breakLine: true } },
    { text: "   \u591A\u6A21\u6001AI + \u5411\u91CF\u68C0\u7D22 + \u56FE\u5F62\u5316\u5C55\u793A" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 1.5,
    fontSize: 11, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Future plans
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 2.3,
    fill: { color: theme.primary }
  });

  slide.addText("\u672A\u6765\u89C4\u5212", {
    x: 5.4, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u25B6 \u589E\u5F3A\u77E5\u8BC6\u56FE\u8C31\u4E92\u52A8", options: { breakLine: true } },
    { text: "\u25B6 \u589E\u52A0\u79BB\u7EBF\u6A21\u5F0F", options: { breakLine: true } },
    { text: "\u25B6 \u6269\u5C55\u5230\u66F4\u591A\u884C\u4E1A", options: { breakLine: true } },
    { text: "\u25B6 AR\u68C0\u4FEE\u8F85\u52A9" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 1.5,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Bottom highlight - core message
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 3.95, w: 9, h: 1.2,
    fill: { color: theme.secondary }
  });

  slide.addText("\u201C\u901A\u8FC7\u667A\u80FD\u5316\u8BBE\u5907\u68C0\u4FEE\uFF0C\u8BA9\u4F01\u4E1A\u77E5\u8BC6\u8D8A\u6765\u8D8A\u6709\u4EF7\u503C\u201D", {
    x: 0.5, y: 4.0, w: 9, h: 0.7,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });

  slide.addText("\u57FA\u4E8E\u591A\u6A21\u6001\u5927\u6A21\u578B\u6280\u672F\uFF0C\u6253\u9020\u4E13\u4E1A\u3001\u9AD8\u6548\u3001\u6613\u7528\u7684\u68C0\u4FEE\u89E3\u51B3\u65B9\u6848", {
    x: 0.5, y: 4.65, w: 9, h: 0.4,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("12", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };