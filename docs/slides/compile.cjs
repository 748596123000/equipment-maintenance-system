const pptxgen = require('pptxgenjs');
const pres = new pptxgen();

pres.layout = 'LAYOUT_16x9';
pres.title = '\u8BBE\u5907\u68C0\u4FEE\u77E5\u8BC6\u68C0\u7D22\u4E0E\u4F5C\u4E1A\u7CFB\u7EDF';
pres.author = '\u9F99\u82AF\u4E2D\u79D1\u6280\u672F\u80A1\u4EFD\u6709\u9650\u516C\u53F8';
pres.subject = '\u7B2C15\u5C4A\u4E2D\u56FD\u8F6F\u4EF6\u676F\u5927\u8D5B';

// Dark theme - professional tech style
const theme = {
  primary: '1a1a2e',     // Dark blue-black
  secondary: '16213e',   // Dark navy
  accent: '0f3460',      // Deep blue
  light: 'e8e8e8',       // Light gray text
  bg: '0f0f1a'           // Near black background
};

// Load and create all slides in order
require('./slide-01.cjs').createSlide(pres, theme);
require('./slide-02.cjs').createSlide(pres, theme);
require('./slide-03.cjs').createSlide(pres, theme);
require('./slide-04.cjs').createSlide(pres, theme);
require('./slide-05.cjs').createSlide(pres, theme);
require('./slide-06.cjs').createSlide(pres, theme);
require('./slide-07.cjs').createSlide(pres, theme);
require('./slide-08.cjs').createSlide(pres, theme);
require('./slide-09.cjs').createSlide(pres, theme);
require('./slide-10.cjs').createSlide(pres, theme);
require('./slide-11.cjs').createSlide(pres, theme);
require('./slide-12.cjs').createSlide(pres, theme);
require('./slide-13.cjs').createSlide(pres, theme);

// Write to output
pres.writeFile({ fileName: './output/\u6F14\u793APPT.pptx' })
  .then(() => {
    console.log('PPTX created successfully: ./output/\u6F14\u793APPT.pptx');
  })
  .catch(err => {
    console.error('Error creating PPTX:', err);
    process.exit(1);
  });