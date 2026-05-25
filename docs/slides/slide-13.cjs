function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Decorative geometric shapes - similar to cover
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3, h: 0.08,
    fill: { color: theme.accent }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.08, h: 2.5,
    fill: { color: theme.accent }
  });

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 7, y: 5.545, w: 3, h: 0.08,
    fill: { color: theme.accent }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 9.92, y: 3.125, w: 0.08, h: 2.5,
    fill: { color: theme.accent }
  });

  // Thank you text
  slide.addText("\u611F\u8C22", {
    x: 0.5, y: 1.3, w: 9, h: 1.2,
    fontSize: 72, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "center", valign: "middle"
  });

  // Divider
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4, y: 2.6, w: 2, h: 0.03,
    fill: { color: theme.accent }
  });

  // Acknowledgments
  slide.addText("\u611F\u8C22\u5927\u8D5B\u59D4\u5458\u4F1A", {
    x: 0.5, y: 2.9, w: 9, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  slide.addText("\u611F\u8C22\u56E2\u961F\u6210\u5458", {
    x: 0.5, y: 3.4, w: 9, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Contact info box
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 2.5, y: 4.1, w: 5, h: 1,
    fill: { color: theme.primary }
  });

  slide.addText("\u8054\u7CFB\u65B9\u5F0F", {
    x: 2.5, y: 4.2, w: 5, h: 0.4,
    fontSize: 12, fontFace: "Microsoft YaHei",
    color: theme.accent, align: "center", valign: "middle"
  });

  slide.addText("\u7B2C15\u5C4A\u4E2D\u56FD\u8F6F\u4EF6\u676F\u5927\u8D5B", {
    x: 2.5, y: 4.55, w: 5, h: 0.5,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("13", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };