const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');

// 应用配置
const CONFIG = {
    PYTHON_BACKEND_PORT: 7860,
    MAX_STARTUP_TIME: 30000, // 30秒
    RETRY_ATTEMPTS: 3,
    RETRY_DELAY: 5000 // 5秒
};

// 全局变量
let mainWindow;
let pythonProcess;
let isBackendReady = false;

// Python后端管理
class PythonBackendManager {
    constructor() {
        this.process = null;
        this.startAttempts = 0;
        this.maxAttempts = CONFIG.RETRY_ATTEMPTS;
    }

    async start() {
        console.log('🚀 启动Python后端服务...');
        
        return new Promise((resolve, reject) => {
            this.startBackend(resolve, reject);
        });
    }

    startBackend(resolve, reject) {
        if (this.startAttempts >= this.maxAttempts) {
            console.error('❌ Python后端启动失败，已达到最大重试次数');
            reject(new Error('Python后端启动失败'));
            return;
        }

        this.startAttempts++;
        console.log(`📶 第 ${this.startAttempts}/${this.maxAttempts} 次尝试启动Python后端...`);

        // 确定Python后端路径
        const isDev = process.env.NODE_ENV === 'development';
        let backendPath;
        let command;
        let args;

        if (isDev) {
            // 开发模式：直接运行Python脚本
            backendPath = path.join(__dirname, '..', 'src', 'main.py');
            command = process.platform === 'win32' ? 'python' : 'python3';
            args = [backendPath];
        } else {
            // 生产模式：运行打包后的可执行文件
            const platform = process.platform;
            const executableName = platform === 'win32' ? 'freeu_backend.exe' : 'freeu_backend';
            backendPath = path.join(process.resourcesPath, 'python_backend', 'dist', executableName);
            command = backendPath;
            args = [];
        }

        console.log(`📝 启动命令: ${command} ${args.join(' ')}`);
        console.log(`📁 工作目录: ${path.dirname(backendPath)}`);

        // 启动Python进程
        this.process = spawn(command, args, {
            cwd: path.dirname(backendPath),
            stdio: ['ignore', 'pipe', 'pipe'],
            env: {
                ...process.env,
                PYTHONUNBUFFERED: '1',
                NODE_ENV: process.env.NODE_ENV
            }
        });

        // 监听输出
        this.process.stdout.on('data', (data) => {
            const output = data.toString();
            console.log(`🐍 Python: ${output}`);
            
            // 检查是否启动成功
            if (output.includes('应用启动成功') || output.includes('Running on local URL')) {
                console.log('✅ Python后端启动成功！');
                this.checkBackendHealth(resolve, reject);
            }
        });

        this.process.stderr.on('data', (data) => {
            console.error(`🐍 Python错误: ${data}`);
        });

        this.process.on('error', (error) => {
            console.error(`❌ Python进程错误: ${error.message}`);
            this.handleStartError(error, resolve, reject);
        });

        this.process.on('exit', (code, signal) => {
            console.log(`🐍 Python进程退出: code=${code}, signal=${signal}`);
            isBackendReady = false;
            
            if (code !== 0 && this.startAttempts < this.maxAttempts) {
                console.log(`⏱️  ${CONFIG.RETRY_DELAY/1000}秒后重试...`);
                setTimeout(() => {
                    this.startBackend(resolve, reject);
                }, CONFIG.RETRY_DELAY);
            }
        });
    }

    async checkBackendHealth(resolve, reject) {
        console.log('🔍 检查后端服务健康状态...');
        
        const maxAttempts = 10;
        let attempts = 0;
        
        const checkHealth = async () => {
            attempts++;
            
            try {
                const response = await axios.get(`http://127.0.0.1:${CONFIG.PYTHON_BACKEND_PORT}/`, {
                    timeout: 3000
                });
                
                if (response.status === 200) {
                    console.log('✅ 后端服务健康检查通过！');
                    isBackendReady = true;
                    resolve();
                    return;
                }
            } catch (error) {
                console.log(`🔍 健康检查第${attempts}次尝试失败: ${error.message}`);
            }
            
            if (attempts < maxAttempts) {
                setTimeout(checkHealth, 2000);
            } else {
                console.error('❌ 后端服务健康检查失败');
                reject(new Error('后端服务启动失败'));
            }
        };
        
        checkHealth();
    }

    handleStartError(error, resolve, reject) {
        console.error(`❌ 启动失败: ${error.message}`);
        
        if (this.startAttempts < this.maxAttempts) {
            console.log(`⏱️  ${CONFIG.RETRY_DELAY/1000}秒后重试...`);
            setTimeout(() => {
                this.startBackend(resolve, reject);
            }, CONFIG.RETRY_DELAY);
        } else {
            reject(error);
        }
    }

    stop() {
        console.log('🛑 停止Python后端服务...');
        
        if (this.process) {
            try {
                this.process.kill('SIGTERM');
                console.log('✅ Python后端服务已停止');
            } catch (error) {
                console.error(`❌ 停止Python后端失败: ${error.message}`);
            }
        }
    }
}

// 创建主窗口
function createMainWindow() {
    console.log('🖥️  创建主窗口...');
    
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 800,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        titleBarStyle: 'default',
        show: false // 等后端准备好再显示
    });

    // 加载Gradio界面
    const grdioUrl = `http://127.0.0.1:${CONFIG.PYTHON_BACKEND_PORT}`;
    console.log(`🌐 加载Gradio界面: ${grdioUrl}`);
    
    mainWindow.loadURL(grdioUrl);

    // 窗口事件
    mainWindow.once('ready-to-show', () => {
        console.log('✅ 主窗口准备就绪');
        mainWindow.show();
        
        if (process.env.NODE_ENV === 'development') {
            mainWindow.webContents.openDevTools();
        }
    });

    mainWindow.on('closed', () => {
        console.log('🪟 主窗口已关闭');
        mainWindow = null;
    });

    // 处理页面加载错误
    mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
        console.error(`❌ 页面加载失败: ${errorCode} - ${errorDescription}`);
        
        if (errorCode === -324 && !isBackendReady) {
            // 后端未准备好，显示等待页面
            mainWindow.loadFile(path.join(__dirname, 'waiting.html'));
        }
    });
}

// IPC事件处理
ipcMain.handle('select-directory', async () => {
    console.log('📁 显示目录选择对话框');
    
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
        title: '选择要整理的目录'
    });
    
    return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('get-app-version', () => {
    return app.getVersion();
});

ipcMain.handle('show-error-dialog', (event, title, content) => {
    dialog.showErrorBox(title, content);
});

// 应用生命周期
app.whenReady().then(async () => {
    console.log('🚀 Electron应用准备就绪');
    
    try {
        // 启动Python后端
        const backendManager = new PythonBackendManager();
        await backendManager.start();
        
        pythonProcess = backendManager;
        
        // 创建主窗口
        createMainWindow();
        
        console.log('✅ 应用启动成功！');
        
    } catch (error) {
        console.error(`❌ 应用启动失败: ${error.message}`);
        
        dialog.showErrorBox(
            '启动失败',
            `无法启动FreeU应用:\n${error.message}\n\n请检查Python环境和依赖是否正确安装。`
        );
        
        app.quit();
    }
});

app.on('window-all-closed', () => {
    console.log('🪟 所有窗口已关闭');
    
    // 停止Python后端
    if (pythonProcess) {
        pythonProcess.stop();
    }
    
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('before-quit', () => {
    console.log('🛑 应用即将退出');
    
    // 确保停止Python后端
    if (pythonProcess) {
        pythonProcess.stop();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

// 错误处理
process.on('uncaughtException', (error) => {
    console.error('❌ 未捕获的异常:', error);
    
    dialog.showErrorBox(
        '应用错误',
        `发生未预期的错误:\n${error.message}`
    );
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ 未处理的Promise拒绝:', reason);
});

console.log('📝 Electron主进程初始化完成');