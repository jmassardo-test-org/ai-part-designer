import path from 'path';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';
// https://vitejs.dev/config/
export default defineConfig(function (_a) {
    var mode = _a.mode;
    // Load env file based on `mode` in the current working directory.
    var env = loadEnv(mode, process.cwd(), '');
    // API target: Check multiple sources for Docker compatibility
    // 1. System env var (set by docker-compose)
    // 2. Loaded from .env file
    // 3. Default to localhost for local dev
    var apiTarget = 'http://localhost:8000';
    // In Docker, VITE_API_PROXY_TARGET will be set
    if (process.env.VITE_API_PROXY_TARGET) {
        apiTarget = process.env.VITE_API_PROXY_TARGET;
    }
    else if (env.VITE_API_PROXY_TARGET) {
        apiTarget = env.VITE_API_PROXY_TARGET;
    }
    return {
        plugins: [react()],
        resolve: {
            alias: {
                '@': path.resolve(__dirname, './src'),
            },
        },
        server: {
            port: 5173,
            proxy: {
                '/api': {
                    target: apiTarget,
                    changeOrigin: true,
                },
            },
        },
        build: {
            // Enable source maps for debugging
            sourcemap: true,
            // Rollup options for code splitting
            rollupOptions: {
                output: {
                    // Manual chunks for better caching
                    manualChunks: {
                        // Vendor chunk for React core
                        'react-vendor': ['react', 'react-dom', 'react-router-dom'],
                        // Three.js and 3D related libraries (lazy loaded)
                        'three-vendor': ['three', '@react-three/fiber', '@react-three/drei', 'three-stdlib'],
                        // Form handling libraries
                        'form-vendor': ['react-hook-form', '@hookform/resolvers', 'zod'],
                        // UI utilities
                        'ui-vendor': ['lucide-react', 'clsx'],
                    },
                },
            },
            // Target modern browsers for smaller bundle
            target: 'es2020',
            // Minification settings
            minify: 'terser',
            terserOptions: {
                compress: {
                    drop_console: true,
                    drop_debugger: true,
                },
            },
            // Chunk size warning limit (500KB)
            chunkSizeWarningLimit: 500,
            // CSS code splitting
            cssCodeSplit: true,
        },
        // Optimize dependencies
        optimizeDeps: {
            include: ['react', 'react-dom', 'react-router-dom'],
            exclude: ['three'], // Exclude three.js for lazy loading
        },
    };
});
