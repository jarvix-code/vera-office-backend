const sharp = require('sharp');
const fs = require('fs');

const svgBuffer = fs.readFileSync('C:/Jarvix/vera-office/static/vera-logo-official.svg');

Promise.all([
  sharp(svgBuffer)
    .resize(512, 512)
    .png()
    .toFile('C:/Jarvix/vera-office/static/vera-logo-official-512.png'),
  
  sharp(svgBuffer)
    .resize(256, 256)
    .png()
    .toFile('C:/Jarvix/vera-office/static/vera-logo-official-256.png'),
  
  sharp(svgBuffer)
    .resize(128, 128)
    .png()
    .toFile('C:/Jarvix/vera-office/static/vera-logo-official-128.png')
]).then(() => {
  console.log('✅ PNG-Versionen erstellt: 512px, 256px, 128px');
}).catch(err => {
  console.error('❌ Fehler:', err);
});
