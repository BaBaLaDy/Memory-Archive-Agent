const { contextBridge, webUtils, shell, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  isElectron: true,
  getFilePath: (file) => webUtils.getPathForFile(file),
  openPath: (path) => shell.openPath(path),
  showItemInFolder: (path) => shell.showItemInFolder(path),
  hideWindow: () => ipcRenderer.send('hide-window'),
  resizeWindow: (size) => ipcRenderer.send('resize-window', size),
  // 右键菜单：弹出文件操作选项
  showFileMenu: (absPath) => ipcRenderer.send('show-file-menu', absPath),
});
