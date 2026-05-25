function createSlide(pres, theme) {
  const slide = pres.addSlide();

  // Dark background
  slide.background = { color: theme.bg };

  // Decorative geometric shapes - top left
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3, h: 0.08,
    fill: { color: theme.accent }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.08, h: 2.5,
    fill: { color: theme.accent }
  });

  // Decorative geometric shapes - bottom right
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 7, y: 5.545, w: 3, h: 0.08,
    fill: { color: theme.accent }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 9.92, y: 3.125, w: 0.08, h: 2.5,
    fill: { color: theme.accent }
  });

  // Small accent circles
  slide.addShape(pres.shapes.OVAL, {
    x: 0.5, y: 0.5, w: 0.15, h: 0.15,
    fill: { color: theme.primary, transparency: 60 }
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 9.2, y: 4.8, w: 0.25, h: 0.25,
    fill: { color: theme.accent, transparency: 40 }
  });

  // Main title
  slide.addText("\u8BBE\u5907\u68C0\u4FEE\u77E5\u8BC6\u68C0\u7D22\u4E0E\u4F5C\u4E1A\u7CFB\u7EDF", {
    x: 0.5, y: 1.8, w: 9, h: 1.2,
    fontSize: 44, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "center", valign: "middle",
    fit: "shrink"
  });

  // Subtitle
  slide.addText("\u57FA\u4E8E\u591A\u6A21\u6001\u5927\u6A21\u578B\u6280\u672F\u7684\u667A\u80FD\u68C0\u4FEE\u65B9\u6848", {
    x: 0.5, y: 3.0, w: 9, h: 0.6,
    fontSize: 22, fontFace: "Microsoft YaHei",
    color: theme.accent, align: "center", valign: "middle"
  });

  // Divider line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3.5, y: 3.8, w: 3, h: 0.03,
    fill: { color: theme.secondary }
  });

  // Team info
  slide.addText("\u7B2C15\u5C4A\u4E2D\u56FD\u8F6F\u4EF6\u676F\u5927\u8D5B - \u9F99\u82AF\u4E2D\u79D1\u6280\u672F\u80A1\u4EFD\u6709\u9650\u516C\u53F8", {
    x: 0.5, y: 4.1, w: 9, h: 0.5,
    fontSize: 16, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle",
    transparency: 30
  });

  // Date
  slide.addText("2026\u5E745\u6708", {
    x: 0.5, y: 4.7, w: 9, h: 0.4,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle",
    transparency: 50
  });
}

module.exports = { createSlide };