function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u79FB\u52A8\u7AEF\u9002\u914D", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Device mockup area
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.4, w: 3.5, h: 3.5,
    fill: { color: theme.primary },
    line: { color: theme.accent, width: 1 }
  });

  // Phone mockup frame
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 1.2, y: 1.6, w: 2.1, h: 3.1,
    fill: { color: theme.bg },
    line: { color: theme.light, width: 1 }
  });

  slide.addText("\u54CD\u5E94\u5F0F\u8BBE\u8BA1", {
    x: 1.2, y: 2.8, w: 2.1, h: 0.8,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });

  slide.addText("PC / \u5E73\u677F / \u624B\u673A", {
    x: 1.2, y: 3.5, w: 2.1, h: 0.5,
    fontSize: 10, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Features on right side
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.3, y: 1.4, w: 5.2, h: 1.6,
    fill: { color: theme.primary }
  });

  slide.addText("\u54CD\u5E94\u5F0F\u8BBE\u8BA1\u7279\u70B9", {
    x: 4.5, y: 1.5, w: 5, h: 0.5,
    fontSize: 16, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", valign: "middle", margin: 0
  });

  slide.addText([
    { text: "\u2022 \u5B8C\u7F8E\u9002\u5E94\u5404\u79CD\u5C4F\u5E55\u5C3A\u5BF8", options: { breakLine: true } },
    { text: "\u2022 \u89E6\u6478\u4F18\u5316\u64CD\u4F5C\u66F4\u987A\u6F01", options: { breakLine: true } },
    { text: "\u2022 \u5B89\u5168\u533A\u57DF\u9002\u914D\u907F\u514D\u88C1\u526A\u60CA\u5F02" }
  ], {
    x: 4.5, y: 2.1, w: 5, h: 0.9,
    fontSize: 13, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Dark mode feature
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.3, y: 3.2, w: 2.5, h: 1.7,
    fill: { color: theme.secondary }
  });

  slide.addText("\u6697\u8272\u4E3B\u9898", {
    x: 4.3, y: 3.3, w: 2.5, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });

  slide.addText("\u4FDD\u62A4\u89C6\u529B\n\u8282\u7701\u80FD\u6E90", {
    x: 4.4, y: 3.8, w: 2.3, h: 1,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Animation feature
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 7, y: 3.2, w: 2.5, h: 1.7,
    fill: { color: theme.secondary }
  });

  slide.addText("\u6D41\u7545\u52A8\u753B", {
    x: 7, y: 3.3, w: 2.5, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "center", valign: "middle"
  });

  slide.addText("\u63D0\u5347\u7528\u6237\n\u4F53\u9A8C\u611F", {
    x: 7.1, y: 3.8, w: 2.3, h: 1,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("09", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };