function createSlide(pres, theme) {
  const slide = pres.addSlide();
  slide.background = { color: theme.bg };

  // Page title
  slide.addText("\u9879\u76EE\u6982\u8FF0", {
    x: 0.5, y: 0.4, w: 9, h: 0.7,
    fontSize: 36, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "left", margin: 0
  });

  // Accent line under title
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.1, w: 1.5, h: 0.05,
    fill: { color: theme.accent }
  });

  // Problem section - left card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.5, w: 4.3, h: 2.4,
    fill: { color: theme.primary }
  });

  slide.addText("\u73B0\u72B6\u4E0E\u6311\u6218", {
    x: 0.7, y: 1.6, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", margin: 0
  });

  slide.addText([
    { text: "\u2022 \u77E5\u8BC6\u5206\u6563\u96C6\u6210\u96C6\u56E0\u91CD\u590D", options: { breakLine: true } },
    { text: "\u2022 \u691C\u7D22\u6548\u7387\u4F4E\u4E0B\u590D\u6742\u68C0\u7D22", options: { breakLine: true } },
    { text: "\u2022 \u65B0\u4EBA\u4E0A\u624B\u6162\u64D2\u672F\u8BBE\u5907\u590D\u6742", options: { breakLine: true } },
    { text: "\u2022 \u7ECF\u9A8C\u4F20\u627F\u56F0\u96BE\u6807\u51C6\u5316\u4F4E" }
  ], {
    x: 0.7, y: 2.1, w: 4, h: 1.8,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Solution section - right card
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: 1.5, w: 4.3, h: 2.4,
    fill: { color: theme.primary }
  });

  slide.addText("\u6838\u5FC3\u4EF7\u503C", {
    x: 5.4, y: 1.6, w: 4, h: 0.5,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.accent, align: "left", margin: 0
  });

  slide.addText([
    { text: "\u2022 \u63D0\u9AD8\u68C0\u4FEE\u6548\u7387\u51CF\u5C11\u505C\u673A\u65F6\u95F4", options: { breakLine: true } },
    { text: "\u2022 \u964D\u4F4E\u64CD\u4F5C\u5931\u8BEC\u7387\u63D0\u5347\u5B89\u5168\u6027", options: { breakLine: true } },
    { text: "\u2022 \u7CBE\u786E\u5339\u914D\u68C0\u4FEE\u65B9\u6848\u63D0\u5347\u51C6\u786E\u5EA6", options: { breakLine: true } },
    { text: "\u2022 \u79EF\u7D2F\u4F01\u4E1A\u77E5\u8BC6\u8D44\u4EA7\u63D0\u5347\u7ADE\u4E89\u529B" }
  ], {
    x: 5.4, y: 2.1, w: 4, h: 1.8,
    fontSize: 14, fontFace: "Microsoft YaHei",
    color: theme.light, align: "left", valign: "top"
  });

  // Bottom highlight bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 4.2, w: 9, h: 1.1,
    fill: { color: theme.secondary }
  });

  slide.addText("\u901A\u8FC7AI\u667A\u80FD\u52A9\u624B\u5B9E\u73B0\u8BBE\u5907\u68C0\u4FEE\u7684\u98CE\u9669\u5F0F\u5347\u7EA7", {
    x: 0.5, y: 4.35, w: 9, h: 0.8,
    fontSize: 18, fontFace: "Microsoft YaHei", bold: true,
    color: theme.light, align: "center", valign: "middle"
  });

  // Page number
  slide.addText("02", {
    x: 9.3, y: 5.1, w: 0.5, h: 0.3,
    fontSize: 12, fontFace: "Arial",
    color: theme.light, align: "right", transparency: 50
  });
}

module.exports = { createSlide };