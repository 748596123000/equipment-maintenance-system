function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u521B\u65B0\u4E0E\u4F18\u52BF", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Technology innovation section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 2.6,
    fill: { color: theme.primary }
  });

  slide.addText("\u6280\u672F\u521B\u65B0", {
    x: 0.7, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u25B6 \u591A\u6A21\u6001\u5927\u6A21\u578B\u878D\u5408", options: { breakLine: true } },
    { text: "   \u6587\u672C\u3001\u56FE\u7247\u3001\u89C6\u9891\u5F02\u6784\u5F0F\u68C0\u7D22", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25B6 \u5411\u91CF\u8BED\u4E49\u68C0\u7D22", options: { breakLine: true } },
    { text: "   \u57FA\u4E8E\u5D4C\u5165\u7684\u8BED\u4E49\u7406\u89E3\u68C0\u7D22", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25B6 \u667A\u80FD\u77E5\u8BC6\u63A8\u8350", options: { breakLine: true } },
    { text: "   \u6839\u636E\u68C0\u4FEE\u5386\u53F2\u63A8\u8350\u76F8\u5173\u6848\u4F8B" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 1.8,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Application value section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 2.6,
    fill: { color: theme.primary }
  });

  slide.addText("\u5E94\u7528\u4EF7\u503C", {
    x: 5.4, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  // Big numbers for impact
  slide.addText("30%+", {
    x: 5.4, y: 2.1, w: 1.8, h: 0.6,
    fontSize: 28, fontFace: "Arial", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });
  slide.addText("\u68C0\u4FEE\u6548\u7387\u63D0\u5347", {
    x: 5.4, y: 2.65, w: 1.8, h: 0.3,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  slide.addText("50%+", {
    x: 7.7, y: 2.1, w: 1.8, h: 0.6,
    fontSize: 28, fontFace: "Arial", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });
  slide.addText("\u64CD\u4F5C\u5931\u8BEF\u7387\u964D\u4F4E", {
    x: 7.7, y: 2.65, w: 1.8, h: 0.3,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  slide.addText("\u2022 \u77E5\u8BC6\u6C89\u6DC0\u4E0E\u590D\u7528\n\u2022 \u6807\u51C6\u5316\u4F5C\u4E1A\u6D41\u7A0B\n\u2022 \u8BAD\u7EC3\u65F6\u957F\u7F29\u77ED", {
    x: 5.4, y: 3.1, w: 4, h: 0.8,
    fontSize: 11, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Bottom comparison bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.25, w: 9, h: 1.05,
    fill: { color: theme.secondary }
  });

  slide.addText("\u4F18\u52BF\u5BF9\u6BD4  |  \u4F20\u7EDF\u65B9\u5F0F  vs  \u672C\u7CFB\u7EDF", {
    x: 0.7, y: 4.35, w: 8.5, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", valign: "middle", margin: 0
  });

  slide.addText("\u4EE5\u56FE\u641C\u56FE  \u2192  \u591A\u6A21\u6001\u68C0\u7D22  |  \u4EE5\u7C7B\u4F3C\u641C\u7D22  \u2192  \u8BED\u4E49\u5339\u914D  |  \u4EE5\u4EBA\u5DE5\u54CD\u5E94  \u2192  AI\u81EA\u52A8\u5316", {
    x: 0.7, y: 4.75, w: 8.5, h: 0.45,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("10", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };