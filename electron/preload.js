const { contextBridge, ipcRenderer } = require('electron');

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
    // 目录选择
    selectDirectory: () => ipcRenderer.invoke('select-directory'),
    
    // 获取应用信息
    getAppVersion: () => ipcRenderer.invoke('get-app-version'),
    
    // 显示错误对话框
    showErrorDialog: (title, content) => ipcRenderer.invoke('show-error-dialog', title, content),
    
    // 监听事件
    on: (channel, func) => {
        const validChannels = [
            'backend-status',
            'operation-progress',
            'error'
        ];
        
        if (validChannels.includes(channel)) {
            ipcRenderer.on(channel, (event, ...args) => func(...args));
        }
    },
    
    // 移除监听器
    removeListener: (channel, func) => {
        ipcRenderer.removeListener(channel, func);
    }
});

// 添加一些实用的全局函数
contextBridge.exposeInMainWorld('utils', {
    // 格式化文件大小
    formatFileSize: (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 格式化日期
    formatDate: (date) => {
        return new Date(date).toLocaleString('zh-CN');
    },
    
    // 检查是否为图片文件
    isImageFile: (filename) => {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'];
        const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        return imageExtensions.includes(ext);
    },
    
    // 获取文件图标（简化版）
    getFileIcon: (filename) => {
        const ext = filename.toLowerCase().substring(filename.lastIndexOf('.') + 1);
        const iconMap = {
            'pdf': '📄',
            'doc': '📝',
            'docx': '📝',
            'txt': '📃',
            'jpg': '🖼️',
            'jpeg': '🖼️',
            'png': '🖼️',
            'gif': '🖼️',
            'mp4': '🎬',
            'avi': '🎬',
            'mp3': '🎵',
            'wav': '🎵',
            'zip': '📦',
            'rar': '📦',
            'xls': '📊',
            'xlsx': '📊',
            'ppt': '📽️',
            'pptx': '📽️'
        };
        
        return iconMap[ext] || '📎';
    }
});

// 日志记录
console.log('🔧 Electron预加载脚本加载完成');