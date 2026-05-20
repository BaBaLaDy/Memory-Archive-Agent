interface ElectronAPI {
  platform: string;
  isElectron: boolean;
  getFilePath: (file: File) => string;
  openPath: (path: string) => Promise<string>;
  showItemInFolder: (path: string) => void;
  hideWindow: () => void;
  resizeWindow: (size: { width: number; height: number }) => void;
}

declare global {
  interface Window {
    electronAPI: ElectronAPI;
  }
}

export {};
