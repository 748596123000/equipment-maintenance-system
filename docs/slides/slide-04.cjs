function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u6838\u5FC3\u529F\u80FD \u4E0A", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Feature 1: Multi-modal Search
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 4.3, h: 3.8,
    fill: { color: theme.primary }
  });

  // Feature 1 number badge
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: theme.accent }
  });
  slide.addText("1", {
    x: 0.5, y: 1.4, w: 0.5, h: 0.5,
    fontSize: 20, fontFace: "Arial", bold: true,
    color: theme.bg, align: "center", valign: "middle"
  });

  slide.addText("\u591A\u6A21\u6001\u77E5\u8BC6\u68C0\u7D22", {
    x: 1.1, y: 1.5, w: 3.5, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2605 \u6587\u672C\u68C0\u7D22", options: { breakLine: true } },
    { text: "   \u8F93\u5165\u5173\u952E\u8BCD\uFF0C\u901A\u8FC7\u5411\u91CF\u5D4C\u5165\u68C0\u7D22\u5E7F\u5927\u77E5\u8BC6\u5E93", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u56FE\u7247\u68C0\u7D22", options: { breakLine: true } },
    { text: "   \u4E0A\u4F20\u6545\u969C\u56FE\u7247\uFF0C\u4EE5\u56FE\u641C\u56FE\u5B9E\u73B0\u76F8\u4F3C\u6848\u4F8B\u68C0\u7D22", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u6DF7\u5408\u68C0\u7D22", options: { breakLine: true } },
    { text: "   \u6587\u672C+\u56FE\u7247\u7ED3\u5408\u68C0\u7D22\uFF0C\u63D0\u5347\u68C0\u7D22\u51C6\u786E\u5EA6", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u5B9E\u65F6\u5386\u53F2", options: { breakLine: true } },
    { text: "   \u8BB0\u5F55\u68C0\u7D22\u5386\u53F2\uFF0C\u5FEB\u901F\u91CD\u590D\u67E5\u8BE2" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 3,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Feature 2: AI Q&A
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 4.3, h: 3.8,
    fill: { color: theme.primary }
  });

  // Feature 2 number badge
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.4, w: 0.5, h: 0.5,
    fill: { color: theme.accent }
  });
  slide.addText("2", {
    x: 5.2, y: 1.4, w: 0.5, h: 0.5,
    fontSize: 20, fontFace: "Arial", bold: true,
    color: theme.bg, align: "center", valign: "middle"
  });

  slide.addText("AI\u667A\u80FD\u95EE\u7B54", {
    x: 5.8, y: 1.5, w: 3.5, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2605 \u81EA\u7136\u8BED\u8A00\u4EA4\u4E92", options: { breakLine: true } },
    { text: "   \u7528\u6237\u8F93\u5165\u95EE\u9898\uFF0C\u7CFB\u7EDF\u81EA\u52A8\u5206\u6790\u5E76\u56DE\u7B54", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u6545\u969C\u8BCA\u65AD\u8F85\u52A9", options: { breakLine: true } },
    { text: "   \u57FA\u4E8E\u77E5\u8BC6\u5E93\uFF0C\u63D0\u4F9B\u6545\u969C\u539F\u56E0\u5206\u6790\u4E0E\u89E3\u51B3\u65B9\u6848", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u591A\u8F6E\u5BF9\u8BDD\u652F\u6301", options: { breakLine: true } },
    { text: "   \u8BB0\u5F55\u5BF9\u8BDD\u5386\u53F2\uFF0C\u7EE7\u7EED\u4E0A\u4E00\u8F6E\u5BF9\u8BDD\u63D0\u5347\u6548\u7387", options: { breakLine: true } },
    { text: "", options: { breakLine: true } },
    { text: "\u2605 \u77E5\u8BC6\u6EAF\u6E90", options: { breakLine: true } },
    { text: "   \u5F15\u7528\u76F8\u5173\u6848\u4F8B\u548C\u6587\u732E\uFF0C\u53EF\u68C0\u7D22\u9605\u8BFB" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 3,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Page number
  slide.addText("04", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };