const { app, BrowserWindow, Tray, Menu, globalShortcut, dialog, nativeImage, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow = null;
let tray = null;
let pythonProcess = null;

const DEV_URL = 'http://localhost:1420';
const API_PORT = 8899;

// ---- Python 后端管理 ----

function findServerPy() {
  // 从项目根找 server.py（electron/../server.py）
  const candidates = [
    path.join(__dirname, '..', 'server.py'),
    path.join(__dirname, '..', '..', 'server.py'),
    path.join(process.cwd(), 'server.py'),
    path.join(process.cwd(), '..', 'server.py'),
  ];
  const fs = require('fs');
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  return null;
}

async function checkBackendRunning() {
  try {
    const http = require('http');
    return await new Promise((resolve) => {
      const req = http.get(`http://127.0.0.1:${API_PORT}/tree`, (res) => {
        resolve(res.statusCode === 200);
      });
      req.on('error', () => resolve(false));
      req.setTimeout(2000, () => { req.destroy(); resolve(false); });
    });
  } catch { return false; }
}

function startPythonBackend() {
  const serverScript = findServerPy();
  if (!serverScript) {
    console.warn('[MAA] 找不到 server.py，跳过启动后端');
    return;
  }

  // 检查是否已有实例在运行
  checkBackendRunning().then((running) => {
    if (running) {
      console.log('[MAA] 后端已在运行，复用现有实例');
      return;
    }
    console.log('[MAA] 启动:', serverScript);
    pythonProcess = spawn('python', [serverScript, '--port', String(API_PORT)], {
      cwd: path.dirname(serverScript),
      stdio: 'pipe',
      env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
    });
    pythonProcess.stdout.on('data', (d) => process.stdout.write(`[MAA] ${d}`));
    pythonProcess.stderr.on('data', (d) => process.stderr.write(`[MAA] ${d}`));
    pythonProcess.on('exit', (code) => {
      console.log('[MAA] 后端退出, code:', code);
      pythonProcess = null;
    });
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
}

// ---- 窗口 ----

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 400,
    height: 56,
    minWidth: 320,
    minHeight: 48,
    title: 'Memory Archive',
    icon: path.join(__dirname, '..', 'src-tauri', 'icons', 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.cjs'),
    },
    frame: false,
    transparent: true,
    resizable: true,
    skipTaskbar: false,
    center: true,
    show: false,
  });

  // 开发模式加载 Vite，生产模式加载打包后的文件
  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL(DEV_URL);
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    mainWindow.focus();
    // DevTools 仅在显式调试时手动打开
  });

  // 关闭窗口时隐藏到托盘，不退出
  mainWindow.on('close', (e) => {
    if (!app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  return mainWindow;
}

// ---- 系统托盘 ----

function createTray() {
  // 用 16x16 的 icon
  const iconPath = path.join(__dirname, '..', 'src-tauri', 'icons', '32x32.png');
  const icon = nativeImage.createFromPath(iconPath);
  tray = new Tray(icon.resize({ width: 16, height: 16 }));
  tray.setToolTip('Memory Archive');

  const menu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        app.isQuitting = true;
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(menu);

  // 左键点击托盘图标显示窗口
  tray.on('click', () => {
    if (mainWindow) {
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

// ---- 全局热键 ----

function registerShortcuts() {
  globalShortcut.register('CommandOrControl+Shift+M', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

// ---- 应用生命周期 ----

ipcMain.on('hide-window', () => {
  if (mainWindow) mainWindow.hide();
});

ipcMain.on('resize-window', (_event, { width, height }) => {
  if (mainWindow) {
    const [x, y] = mainWindow.getPosition();
    // 保持窗口顶部位置不变，向下扩展
    mainWindow.setBounds({ x, y, width, height });
  }
});

// 右键菜单：文件操作
ipcMain.on('show-file-menu', (_event, absPath) => {
  const Menu = require('electron').Menu;
  const menu = Menu.buildFromTemplate([
    {
      label: '打开文件',
      click: () => {
        require('electron').shell.openPath(absPath).then(err => {
          if (err) require('electron').dialog.showErrorBox('打开失败', err);
        });
      },
    },
    {
      label: '定位文件',
      click: () => {
        require('electron').shell.showItemInFolder(absPath);
      },
    },
    {
      label: '复制路径',
      click: () => {
        require('electron').clipboard.writeText(absPath);
      },
    },
  ]);
  if (mainWindow) menu.popup({ window: mainWindow });
});

app.whenReady().then(() => {
  startPythonBackend();
  createWindow();
  createTray();
  registerShortcuts();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  stopPythonBackend();
});

app.on('window-all-closed', () => {
  // macOS 不退出
  if (process.platform !== 'darwin') {
    // 不自动退出，托盘常驻
  }
});

// macOS 激活时重显示窗口
app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
  }
});
