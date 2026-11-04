import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
await mkdir('desktop', { recursive: true });
await mkdir('web', { recursive: true });
await build({ entryPoints:['ui/desktop-entry.js'], outfile:'desktop/plugin.js', bundle:true, format:'esm', platform:'browser', target:'es2022', external:['@hermes/plugin-sdk','react','react/jsx-runtime'], minify:false, legalComments:'inline', charset:'utf8' });
await build({ entryPoints:['ui/dev-entry.js'], outfile:'web/app.js', bundle:true, format:'esm', platform:'browser', target:'es2022', minify:false, legalComments:'inline', charset:'utf8', define:{'process.env.NODE_ENV':'"production"'} });
console.log('Built native Desktop plugin and shared standalone workbench.');
