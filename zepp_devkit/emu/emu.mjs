#!/usr/bin/env node
/**
 * Run apps and watch faces on the real Zepp OS firmware, headless, in the QEMU emulator that
 * ships with Zepp's simulator (Amazfit Balance 2 image: 480x480 round, Zepp OS 5). This is
 * the same firmware a watch runs: real text placement, arc drawing, edit mode and data
 * binding. There is no phone, so an app's side service and settings page don't run here,
 * and sensors the emulator doesn't feed (compass, gyro) read 0.
 *
 * Run from the project's folder (zepp-devkit emu ... runs this with node). Its files live in
 * <project>/tools/.emu/ (ZEPP_EMU_DIR to change; a second watch model's files apart, e.g.
 * tools/.emu-active2 with ZEPP_EMU_MODEL='Active 2'). Needs the `ws` npm package in the project.
 *
 *   zepp-devkit emu setup                     download the emulator + firmware into tools/.emu/
 *   zepp-devkit emu start [--time ISO]        boot it (virtual display :99), wait until ready
 *   zepp-devkit emu stop
 *   zepp-devkit emu install <dir> [--no-build]   zeus build, then install (a project folder, or a
 *                                                    folder's name one level down: faces/<face>); a watch
 *                                                    face is also switched to
 *   zepp-devkit emu apps                      open the app list (then tap the app's icon)
 *   zepp-devkit emu shot <out.png>            screenshot (480x480)
 *   zepp-devkit emu set key=value ...         sensor/user values, e.g. walkstep=12486 btcon=false
 *   zepp-devkit emu tap <x> <y> [seconds]     touch (long-press with seconds >= 2)
 *   zepp-devkit emu swipe <x1> <y1> <x2> <y2> [ms]   ms >= 800: slow drag, no fling
 *   zepp-devkit emu key <qemu key> [ms]       button: ret = select (opens the app list from the face)
 *   zepp-devkit emu face                      back to the watch face (from the app list etc.)
 *   zepp-devkit emu enable-aod                turn on the always-on screen (fresh watch), then:
 *   zepp-devkit emu save-base                 stop and keep this watch state as tools/.emu/base-flash.bin
 *   zepp-devkit emu reset                     stop and restore base-flash.bin (or the factory image)
 *   zepp-devkit emu rest                      screen off: shows the always-on screen once AOD is on
 *
 * Needs Linux x86_64 plus: libvte-2.91-0, libaio1t64 (or libaio1), xvfb, xdotool, python3 with Pillow.
 * See the zepp-devkit README, "The emulator", and the project's own notes on its quirks.
 */
import { execFileSync, spawn } from 'node:child_process';
import fs from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

// the project's folder; `ws` comes from its node_modules
const REPO = path.resolve(process.env.ZEPP_PROJECT || process.cwd());
const HERE = path.dirname(fileURLToPath(import.meta.url));
let WebSocket;
try {
  WebSocket = createRequire(path.join(REPO, 'package.json'))('ws');
} catch {
  console.error('needs the ws package in the project: npm install --save-dev ws');
  process.exit(1);
}
// ZEPP_EMU_DIR keeps a second watch model's files apart (e.g. tools/.emu-active2 with ZEPP_EMU_MODEL='Active 2')
const EMU = process.env.ZEPP_EMU_DIR ? path.resolve(process.env.ZEPP_EMU_DIR) : path.join(REPO, 'tools/.emu');
const QEMU_DIR = path.join(EMU, 'qemu');
const MON = path.join(EMU, 'monitor.sock');
const FLASH = path.join(EMU, 'flash.bin');
const DISPLAY = ':99';
const PORT = 7833;
const MENU_BAR = 25;                         // QEMU's GTK window draws a menu bar above the screen
const SIM_DEB = process.env.ZEPP_SIM_DEB
  || 'https://upload-cdn.zepp.com/zepp-applet-and-wechat-applet/20260717/simulator_2.1.2_linux_amd64.deb';
const DEVICE_LIST = 'https://upload-cdn.huami.com/zeppos/simulator/download/emulatorList.json';
const MODEL = process.env.ZEPP_EMU_MODEL || 'Balance2';

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const run = (cmd, args, opts = {}) => execFileSync(cmd, args, { stdio: 'inherit', ...opts });

// curl rather than fetch(): curl honours HTTPS_PROXY, Node's fetch doesn't
async function download(url, dest) {
  console.log(`downloading ${url}`);
  run('curl', ['-fsSL', '-o', dest, url]);
}

// ------------------------------------------------------------------ setup
async function setup() {
  fs.mkdirSync(EMU, { recursive: true });
  const deb = path.join(EMU, 'simulator.deb');
  if (!fs.existsSync(path.join(QEMU_DIR, 'qemu-system-arm'))) {
    if (!fs.existsSync(deb)) await download(SIM_DEB, deb);
    const x = path.join(EMU, 'deb');
    fs.rmSync(x, { recursive: true, force: true });
    run('dpkg-deb', ['-x', deb, x]);
    fs.cpSync(path.join(x, 'opt/simulator/resources/firmware/qemu_linux'), QEMU_DIR, { recursive: true });
    fs.rmSync(x, { recursive: true, force: true });
    fs.chmodSync(path.join(QEMU_DIR, 'qemu-system-arm'), 0o755);
  }
  // Ubuntu 24.04 renamed libaio.so.1; point the bundled QEMU at the new name.
  const aio = '/usr/lib/x86_64-linux-gnu/libaio.so.1t64';
  const link = path.join(QEMU_DIR, 'lib/libaio.so.1');
  if (fs.existsSync(aio) && !fs.existsSync(link)) fs.symlinkSync(aio, link);

  const fwRoot = path.join(EMU, 'fw');
  if (!fs.existsSync(path.join(fwRoot, 'main.elf'))) {
    const list = JSON.parse(execFileSync('curl', ['-fsSL', DEVICE_LIST]).toString());
    const model = list.find((m) => m.modelName === MODEL);
    if (!model) throw new Error(`no emulator image for ${MODEL}`);
    const rel = model.released.filter((r) => !r.hide)[0];
    const zip = path.join(EMU, 'fw.zip');
    await download(rel.filePath, zip);
    const x = path.join(EMU, 'fwx');
    fs.rmSync(x, { recursive: true, force: true });
    run('unzip', ['-q', zip, '-d', x]);
    const elf = execFileSync('find', [x, '-name', 'main.elf']).toString().trim().split('\n')[0];
    fs.rmSync(fwRoot, { recursive: true, force: true });
    fs.cpSync(path.dirname(elf), fwRoot, { recursive: true });
    fs.rmSync(x, { recursive: true, force: true });
    fs.rmSync(zip);
    fs.writeFileSync(path.join(fwRoot, 'VERSION'), `${rel.name}\n`);
    console.log(`firmware: ${rel.name}`);
  }
  const missing = execFileSync('ldd', [path.join(QEMU_DIR, 'qemu-system-arm')], {
    env: { ...process.env, LD_LIBRARY_PATH: path.join(QEMU_DIR, 'lib') },
  }).toString().split('\n').filter((l) => l.includes('not found'));
  if (missing.length) console.log(`missing libraries (apt install libvte-2.91-0 libaio1t64):\n${missing.join('\n')}`);
  else console.log('emulator ready: zepp-devkit emu start');
}

// ------------------------------------------------------------------ start / stop
async function waitForPort(seconds) {
  const until = Date.now() + seconds * 1000;
  while (Date.now() < until) {
    const ok = await new Promise((resolve) => {
      const ws = new WebSocket(`ws://localhost:${PORT}/SIMULATOR`);
      const t = setTimeout(() => { ws.terminate(); resolve(false); }, 3000); // a reset can leave it hanging
      ws.on('open', () => { clearTimeout(t); ws.close(); resolve(true); });
      ws.on('error', () => { clearTimeout(t); resolve(false); });
    });
    if (ok) return true;
    await sleep(1000);
  }
  return false;
}

// Newer firmware takes its address from QEMU's DHCP (10.0.2.15); older images (Zepp OS 3.x,
// e.g. GTS 4) use a fixed 192.168.166.188, so the port forward must point there.
function guestIp() {
  try {
    const m = [...fs.readFileSync(path.join(EMU, 'serial.log'), 'latin1').matchAll(/Get IP: (\d+\.\d+\.\d+\.\d+)/g)]
    return m.length ? m[m.length - 1][1] : null
  } catch { return null }
}

function nic(ip) {
  if (!ip || ip.startsWith('10.0.2.')) return `user,id=usernet,hostfwd=tcp::${PORT}-:${PORT},model=lan9118`;
  const net = ip.split('.').slice(0, 3).join('.');
  return `user,id=usernet,net=${net}.0/24,host=${net}.2,hostfwd=tcp::${PORT}-${ip}:${PORT},model=lan9118`;
}

async function start(args, ip = null) {
  const timeIdx = args.indexOf('--time');
  const rtc = timeIdx >= 0 ? ['-rtc', `base=${args[timeIdx + 1]}`] : [];
  if (!fs.existsSync(FLASH)) fs.copyFileSync(path.join(EMU, 'fw/norflash.bin'), FLASH);
  try { execFileSync('pgrep', ['-x', 'Xvfb']); } catch {
    spawn('Xvfb', [DISPLAY, '-screen', '0', '800x700x24'], { detached: true, stdio: 'ignore' }).unref();
  }
  // QEMU's GTK window exits at once if the display isn't up yet: wait for its socket
  for (let i = 0; i < 50 && !fs.existsSync(`/tmp/.X11-unix/X${DISPLAY.slice(1)}`); i++) await sleep(200);
  await sleep(500);
  const qemu = spawn(path.join(QEMU_DIR, 'qemu-system-arm'), [
    '-M', 'mps2-an521', '-semihosting',
    '-drive', `file=${FLASH},bus=0,unit=0,format=raw`,
    '-kernel', path.join(EMU, 'fw/main.elf'),
    '-nic', nic(ip),
    '-display', 'gtk,show-cursor=on', '-name', 'Zepp OS Simulator',
    '-monitor', `unix:${MON},server,nowait`,
    '-serial', `file:${path.join(EMU, 'serial.log')}`,
    ...rtc,
  ], {
    detached: true, stdio: 'ignore',
    env: { ...process.env, DISPLAY, LD_LIBRARY_PATH: path.join(QEMU_DIR, 'lib') },
  });
  qemu.unref();
  console.log('booting (about 40 s)...');
  if (!(await waitForPort(ip ? 150 : 100))) {
    const seen = guestIp();
    if (!ip && seen && !seen.startsWith('10.0.2.')) {
      console.log(`firmware uses a fixed address (${seen}): restarting with the port forwarded there`);
      await monitor('quit').catch(() => {});
      await sleep(2000);
      return start(args, seen);
    }
    throw new Error('emulator did not come up; see tools/.emu/serial.log');
  }
  await sleep(8000);                         // let the launcher finish drawing
  console.log(`emulator ready. Firmware log: ${path.relative(REPO, path.join(EMU, 'serial.log'))}`);
}

async function monitor(cmd) {
  await new Promise((resolve, reject) => {
    const s = net.createConnection(MON, () => { s.write(`${cmd}\n`); setTimeout(() => { s.end(); resolve(); }, 400); });
    s.on('error', reject);
  });
}

// ------------------------------------------------------------------ device protocol
async function send(messages, waitMs = 1500) {
  const ws = new WebSocket(`ws://localhost:${PORT}/SIMULATOR`);
  await new Promise((resolve, reject) => { ws.on('open', resolve); ws.on('error', reject); });
  for (const m of messages) {
    await new Promise((resolve) => ws.send(m, resolve));
    await sleep(waitMs);
  }
  ws.close();
}

function projectDir(name) {
  const direct = path.resolve(REPO, name);
  if (fs.existsSync(path.join(direct, 'app.json'))) return direct;
  for (const d of fs.readdirSync(REPO, { withFileTypes: true })) {  // e.g. faces/<face>
    const p = path.join(REPO, d.name, name);
    if (d.isDirectory() && !d.name.startsWith('.') && fs.existsSync(path.join(p, 'app.json'))) return p;
  }
  throw new Error(`no app.json in ${name}/ (or one level down)`);
}

async function install(app, args = []) {
  if (!app || app.startsWith('--')) throw new Error('install <dir>: the project folder (with app.json)');
  const faceDir = projectDir(app);
  const isFace = JSON.parse(fs.readFileSync(path.join(faceDir, 'app.json'), 'utf8')).app.appType === 'watchface';
  app = path.basename(faceDir);
  if (!args.includes('--no-build')) {
    fs.rmSync(path.join(faceDir, 'dist'), { recursive: true, force: true });
    run('zeus', ['build'], { cwd: faceDir, stdio: ['ignore', 'ignore', 'inherit'] });
  }
  const zip = path.join(EMU, `${app}.zip`);
  const appId = execFileSync('python3', [path.join(HERE, 'prepare.py'), faceDir, zip,
    ...(process.env.ZEPP_DEVICE_SOURCE ? ['--device-source', process.env.ZEPP_DEVICE_SOURCE] : [])]).toString().trim();
  const hex = Number(appId).toString(16).toUpperCase().padStart(8, '0');
  const file = fs.readFileSync(zip);
  const head = Buffer.from(`{"method":"Project","type":"install","appid":"${hex}","length":${file.length},"file":"`);
  if (isFace) {
    await send([Buffer.concat([head, file, Buffer.from('"}')]), JSON.stringify({ method: 'ChangeWatchFace', appid: hex })]);
    await toFace();
    console.log(`installed ${app} (${hex})`);
  } else {
    await send([Buffer.concat([head, file, Buffer.from('"}')])]);
    await sleep(4000);
    console.log(`installed ${app} (${hex}); open it from the app list: emu apps, then tap its icon`);
  }
}

async function setValues(pairs) {
  // Defaults and names come from Zepp's simulator; send the full set every time.
  const defaults = {
    calorie: 300, heartrate: 75, walkstep: 300, battery: 88, distance: 885, pai: 75, timeformat: true,
    language: 2, charge: false, btcon: true, mute: false, lock: false, alarm: false, weather: 0, temp: 25,
    aqi: 133, tempmax: 29, tempmin: 22, f_temphl: true, f_weather: true, f_tempnow: true, f_aqi: true,
    uvi: 4, humidity: 50, sunrise_h: 6, sunrise_m: 30, sunset_h: 18, sunset_m: 30, window_level: 4,
    window_dir: 4, moon_phase: 4, alarm_h: 8, alarm_m: 30, goal_calorie: 800, goal_walkstep: 10000,
    stand: 2, goal_stand: 12, sleep_h: 7, sleep_m: 30, goal_sleep: 8, floor: 10, stress: 10,
    fat_burn: 10, goal_fat_burn: 30, spo2: 98, baro: 1013, training_load: 50,
  };
  const types = { timeformat: 'bool', charge: 'bool', btcon: 'bool', mute: 'bool', lock: 'bool', alarm: 'bool',
    f_temphl: 'bool', f_weather: 'bool', f_tempnow: 'bool', f_aqi: 'bool', calorie: 'string' };
  const values = { ...defaults };
  for (const kv of pairs) {
    const [k, v] = kv.replace(/^vcfg_/, '').split('=');
    if (!(k in defaults)) throw new Error(`unknown key ${k}; known: ${Object.keys(defaults).join(' ')}`);
    values[k] = v;
  }
  let str = '{';
  for (const [k, v] of Object.entries(values)) str += `vcfg_${k}|${types[k] || 'int32'}|${v}\r\n`;
  str += '}';
  await send([JSON.stringify({ method: 'Config', vconfig: 'buffer' }).replace('buffer', str)], 3000);
}

// ------------------------------------------------------------------ screen and input
async function shot(out, quiet = false) {
  const ppm = path.join(EMU, 'shot.ppm');
  fs.rmSync(ppm, { force: true });
  await monitor(`screendump ${ppm}`);
  for (let i = 0; i < 20 && !fs.existsSync(ppm); i++) await sleep(100);
  await sleep(300);
  // QEMU dumps rows of width*3 bytes, but the firmware pads each row to 4 bytes (466-wide
  // screens: 1400, not 1398), so re-slice the bytes with the padded stride
  execFileSync('python3', ['-c', [
    'import sys; from PIL import Image',
    'im = Image.open(sys.argv[1]); w, h = im.size; b = im.tobytes(); st = (w * 3 + 3) // 4 * 4',
    'h = min(h, len(b) // st)',
    "im = Image.frombytes('RGB', (w, h), b''.join(b[r * st:r * st + w * 3] for r in range(h))) if st != w * 3 else im",
    'im.save(sys.argv[2])',
  ].join('\n'), ppm, out]);
  if (!quiet) console.log(out);
}

function xdo(args) { execFileSync('xdotool', args, { env: { ...process.env, DISPLAY } }); }

async function tap(x, y, seconds = 0.15) {
  xdo(['mousemove', String(x), String(Number(y) + MENU_BAR), 'mousedown', '1']);
  await sleep(Number(seconds) * 1000);
  xdo(['mouseup', '1']);
  await sleep(1500);
}

async function swipe(x1, y1, x2, y2, ms = 250) {
  // ms >= 800 drags slowly and pauses before lifting, so lists scroll without a fling
  [x1, y1, x2, y2, ms] = [x1, y1, x2, y2, ms].map(Number);
  const steps = Math.max(10, Math.round(ms / 25));
  xdo(['mousemove', String(x1), String(y1 + MENU_BAR), 'mousedown', '1']);
  for (let i = 1; i <= steps; i++) {
    xdo(['mousemove', String(Math.round(x1 + (x2 - x1) * i / steps)), String(Math.round(y1 + MENU_BAR + (y2 - y1) * i / steps))]);
    await sleep(ms / steps);
  }
  if (ms >= 800) await sleep(400);
  xdo(['mouseup', '1']);
  await sleep(1500);
}

// ------------------------------------------------------------------ watch setup
/** Turn on the always-on screen (Settings > Display > Always On Display): scheduled
 * 08:00-22:00, following the watch face. Coordinates are for the Balance 2 v1.1.0 image
 * on a fresh watch. Run once, then `save-base` so `reset` starts from this state. */
async function enableAod() {
  const back = () => swipe(5, 240, 300, 240);
  await monitor('sendkey home 100'); await sleep(2000);       // upper button: app list
  await tap(240, 240);                                       // Settings
  await tap(190, 377);                                       // Display
  await swipe(240, 420, 240, 270, 1200);                     // scroll 150px
  await tap(200, 383);                                       // Always On Display
  await tap(200, 370);                                       // Enable Status
  await tap(68, 370);                                        // Scheduled
  await tap(298, 430);                                       // confirm battery warning
  await back();
  await tap(200, 242);                                       // Always On Style
  await tap(68, 242);                                        // Follow Watch Face
  for (let i = 0; i < 3; i++) await back();
  await toFace();
}

async function onAppList() {
  // The emulated watch has one app, so its app list is a grey Settings icon on the left
  // and black above and below it.
  const file = path.join(EMU, 'probe.png');
  await shot(file, true);
  const out = execFileSync('python3', ['-c', `
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert('L')
icon = sum(im.getpixel((x, y)) for x in range(40, 120, 8) for y in range(200, 280, 8)) / 100
top = max(im.getpixel((x, y)) for x in range(150, 330, 6) for y in range(40, 140, 6))
print(1 if icon > 120 and top < 30 else 0)`, file]).toString().trim();
  return out === '1';
}

async function toFace() {
  // Both buttons toggle between the face and the app list, so look before pressing.
  for (let i = 0; i < 3 && (await onAppList()); i++) {
    await monitor('sendkey backspace 100');
    await sleep(1500);
  }
}

const BASE = path.join(EMU, 'base-flash.bin');

// ------------------------------------------------------------------ main
const [cmd, ...args] = process.argv.slice(2);
const commands = {
  setup: () => setup(),
  start: () => start(args),
  stop: () => monitor('quit').catch(() => {}),
  install: () => install(args[0], args.slice(1)),
  apps: async () => { await toFace(); await monitor('sendkey home 100'); await sleep(2000); },
  shot: () => shot(path.resolve(args[0] || 'emu.png')),
  set: () => setValues(args),
  tap: () => tap(args[0], args[1], args[2]),
  swipe: () => swipe(...args),
  'enable-aod': () => enableAod(),
  'save-base': async () => { await monitor('quit').catch(() => {}); await sleep(2000); fs.copyFileSync(FLASH, BASE); console.log('saved', BASE); },
  reset: async () => {
    await monitor('quit').catch(() => {}); await sleep(2000);
    fs.copyFileSync(fs.existsSync(BASE) ? BASE : path.join(EMU, 'fw/norflash.bin'), FLASH);
    console.log(`watch reset to ${fs.existsSync(BASE) ? 'base-flash.bin' : 'factory state'}`);
  },
  face: () => toFace(),
  key: () => monitor(`sendkey ${args[0]} ${args[1] || 100}`),
  rest: () => send([JSON.stringify({ method: 'ScreenRest' })], 2000),
};
if (!commands[cmd]) {
  console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('*/')[0]);
  process.exit(cmd ? 1 : 0);
}
commands[cmd]().catch((e) => { console.error(e.message || e); process.exit(1); });
