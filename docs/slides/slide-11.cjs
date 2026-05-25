function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u6F14\u793A\u8BA1\u5212", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Demo steps - numbered list
  const steps = [
    { num: "1", title: "\u767B\u5F55\u7CFB\u7EDF", desc: "\u5C55\u793A\u754C\u9762\u4E0E\u8BA4\u8BC1" },
    { num: "2", title: "\u4EEA\u8868\u76D8", desc: "\u5C55\u793A\u6570\u636E\u6982\u89C8\u4E0E\u667A\u80FD\u63A8\u8350" },
    { num: "3", title: "\u77E5\u8BC6\u68C0\u7D22", desc: "\u6F14\u793A\u6587\u672C/\u56FE\u7247\u641C\u7D22" },
    { num: "4", title: "AI\u95EE\u7B54", desc: "\u6F14\u793A\u6545\u969C\u8BCA\u65AD" },
    { num: "5", title: "\u4F5C\u4E1A\u6307\u5F15", desc: "\u6F14\u793A\u6307\u5BFC\u4E66\u751F\u6210" },
    { num: "6", title: "\u6587\u6863\u4E0A\u4F20", desc: "\u6F14\u793A\u77E5\u8BC6\u6C89\u6DC0\u6D41\u7A0B" },
    { num: "7", title: "\u6D88\u606F\u901A\u77E5", desc: "\u6F14\u793A\u53CC\u5411\u901A\u77E5" }
  ];

  const rowH = 0.55;
  const startY = 1.35;

  steps.forEach((step, i) => {
    const y = startY + i * rowH;
    const isEven = i % 2 === 0;

    // Background strip
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: y, w: 9, h: rowH - 0.05,
      fill: { color: isEven ? theme.primary : theme.secondary, transparency: isEven ? 0 : 50 }
    });

    // Number badge
    slide.addShape(pres.shapes.OVAL, {
      x: 0.65, y: y + 0.08, w: 0.35, h: 0.35,
      fill: { color: theme.accent }
    });
    slide.addText(step.num, {
      x: 0.65, y: y + 0.08, w: 0.35, h: 0.35,
      fontSize: 14, fontFace: "Arial", bold: true,
      color: theme.bg, align: "center", valign: "middle"
    });

    // Step title
    slide.addText(step.title, {
      x: 1.2, y: y, w: 2, h: rowH - 0.05,
      fontSize: 14, fontFace: "Microsoft YaHei", bold: true,
      color: theme.light, align: "left", valign: "middle", margin: 0
    });

    // Arrow
    slide.addText("\u2192", {
      x: 3.2, y: y, w: 0.5, h: rowH - 0.05,
      fontSize: 16, fontFace: "Arial",
      color: theme.accent, align: "center", valign: "middle"
    });

    // Description
    slide.addText(step.desc, {
      x: 3.8, y: y, w: 5.5, h: rowH - 0.05,
      fontSize: 13, fontFace: "Microsoft YaHei",
      color: theme.light, align: "left", valign: "middle", transparency: 30, margin: 0
    });
  });

  // Duration note
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 5.15, w: 9, h: 0.3,
    fill: { color: theme.accent, transparency: 80 }
  });
  slide.addText("\u9884\u8BA1\u6F14\u793A\u65F6\u957F\uff1a7\u5206\u949F  |  \u6BCF\u6B65\u7EA730\u79D2", {
    x: 0.5, y: 5.15, w: 9, h: 0.3,
    fontSize: 11, fontFace: "Microsoft YaHei",
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("11", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };