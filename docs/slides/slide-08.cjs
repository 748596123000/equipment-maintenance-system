function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u5B89\u5168\u4E0E\u6743\u9650", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Authentication section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 3.2,
    fill: { color: theme.primary }
  });

  slide.addText("\u7528\u6237\u8BA4\u8BC1", {
    x: 0.7, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u25C9 Bearer Token\u8BA4\u8BC1", options: { breakLine: true } },
    { text: "   JWT\u6807\u8BB6\u5E94\u7528\u8FC7\u7A0B\u9AD8\u5B89\u5168\u6027", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25C9 \u5BC6\u7801\u52A0\u5BC6\u5B58\u50A8", options: { breakLine: true } },
    { text: "   bcrypt\u52A0\u5BC6\u7B97\u6CD5\u9632\u6B62\u660E\u6587\u6CC4\u6F0F", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25C9 \u9A8C\u8BC1\u7801\u9632\u62A4", options: { breakLine: true } },
    { text: "   \u56FE\u5F62\u9A8C\u8BC1\u7801\u9632\u6B62\u66FC\u8BBE\u653B\u51FB" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 2.4,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Permission management section
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 3.2,
    fill: { color: theme.primary }
  });

  slide.addText("\u6743\u9650\u7BA1\u7406", {
    x: 5.4, y: 1.5, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u25C9 \u7BA1\u7406\u5458\u5BA1\u6838", options: { breakLine: true } },
    { text: "   \u6587\u6863\u4E0A\u4F20\u9700\u7BA1\u7406\u5458\u5BA1\u6838\u540E\u624D\u80FD\u53D1\u5E03", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25C9 \u7528\u6237\u7B49\u7EA7\u63A7\u5236", options: { breakLine: true } },
    { text: "   \u521D\u7EA7/\u4E2D\u7EA7/\u9AD8\u7EA7\u68C0\u4FEE\u4EBA\u5458\u8BBE\u7F6E\u4E0D\u540C\u6743\u9650", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u25C9 API\u5B89\u5168\u9632\u62A4", options: { breakLine: true } },
    { text: "   CORS\u8BBE\u7F6E\u3001\u8BF7\u6C42\u9664\u5E1D\u3001\u9891\u7387\u9650\u5236" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 2.4,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Bottom security bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.9, w: 9, h: 0.45,
    fill: { color: theme.secondary }
  });
  slide.addText("\u5B89\u5168\u8BBE\u8BA1\u539F\u5219  |  \u201C\u6700\u5C0F\u6743\u9650\u201D\u3001\u201C\u9AD8\u5B89\u5168\u201D\u3001\u201C\u53EF\u7BA1\u7406\u201D", {
    x: 0.5, y: 4.9, w: 9, h: 0.45,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("08", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };