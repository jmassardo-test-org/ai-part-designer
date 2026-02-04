#!/usr/bin/env node
/**
 * Import Validation Script.
 * 
 * Validates that all external package imports can be resolved.
 * This catches missing dependencies that might be hidden by test mocks.
 * 
 * Run: node scripts/validate-imports.js
 */

import { readFileSync, readdirSync, statSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const SRC = join(ROOT, 'src');

// External packages that should be installed (from package.json)
const packageJson = JSON.parse(readFileSync(join(ROOT, 'package.json'), 'utf-8'));
const installedPackages = new Set([
  ...Object.keys(packageJson.dependencies || {}),
  ...Object.keys(packageJson.devDependencies || {}),
]);

// Add Node.js built-ins
const nodeBuiltins = new Set([
  'fs', 'path', 'url', 'util', 'events', 'stream', 'buffer', 
  'crypto', 'os', 'child_process', 'http', 'https', 'net', 'tls',
  'dns', 'readline', 'zlib', 'assert', 'querystring', 'string_decoder',
]);

// Regex to match import statements
const importRegex = /(?:import|export)\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+)?['"]([^'"]+)['"]/g;
const requireRegex = /require\s*\(\s*['"]([^'"]+)['"]\s*\)/g;

/**
 * Get all TypeScript/JavaScript files recursively
 */
function getFiles(dir, files = []) {
  const items = readdirSync(dir);
  for (const item of items) {
    const path = join(dir, item);
    if (statSync(path).isDirectory()) {
      if (!item.startsWith('.') && item !== 'node_modules') {
        getFiles(path, files);
      }
    } else if (/\.(tsx?|jsx?|mjs)$/.test(item)) {
      files.push(path);
    }
  }
  return files;
}

/**
 * Extract imports from a file
 */
function extractImports(filePath) {
  const content = readFileSync(filePath, 'utf-8');
  const imports = new Set();
  
  let match;
  while ((match = importRegex.exec(content)) !== null) {
    imports.add(match[1]);
  }
  while ((match = requireRegex.exec(content)) !== null) {
    imports.add(match[1]);
  }
  
  return imports;
}

/**
 * Get the package name from an import path
 * e.g., '@tanstack/react-query' -> '@tanstack/react-query'
 * e.g., 'recharts' -> 'recharts'
 * e.g., 'recharts/types' -> 'recharts'
 */
function getPackageName(importPath) {
  if (importPath.startsWith('@')) {
    // Scoped package: @scope/package or @scope/package/subpath
    const parts = importPath.split('/');
    return parts.slice(0, 2).join('/');
  }
  // Regular package: package or package/subpath
  return importPath.split('/')[0];
}

/**
 * Check if an import is external (not relative or alias)
 */
function isExternalImport(importPath) {
  // Relative imports
  if (importPath.startsWith('.') || importPath.startsWith('/')) {
    return false;
  }
  // Path aliases (configured in tsconfig)
  if (importPath.startsWith('@/')) {
    return false;
  }
  return true;
}

// Main validation
console.log('🔍 Validating package imports...\n');

const files = getFiles(SRC);
const missingPackages = new Map(); // package -> [files using it]
let totalImports = 0;

for (const file of files) {
  const imports = extractImports(file);
  const relativePath = file.replace(ROOT + '/', '');
  
  for (const importPath of imports) {
    if (!isExternalImport(importPath)) continue;
    
    totalImports++;
    const packageName = getPackageName(importPath);
    
    // Skip Node.js built-ins
    if (nodeBuiltins.has(packageName)) continue;
    
    // Check if package is in dependencies
    if (!installedPackages.has(packageName)) {
      if (!missingPackages.has(packageName)) {
        missingPackages.set(packageName, []);
      }
      missingPackages.get(packageName).push(relativePath);
    }
  }
}

console.log(`📦 Scanned ${files.length} files with ${totalImports} external imports\n`);

if (missingPackages.size > 0) {
  console.error('❌ Missing packages detected:\n');
  for (const [pkg, usedIn] of missingPackages) {
    console.error(`  📦 ${pkg}`);
    for (const file of usedIn.slice(0, 3)) {
      console.error(`     └─ ${file}`);
    }
    if (usedIn.length > 3) {
      console.error(`     └─ ... and ${usedIn.length - 3} more files`);
    }
  }
  console.error('\n💡 Fix: npm install ' + [...missingPackages.keys()].join(' '));
  process.exit(1);
} else {
  console.log('✅ All package imports are valid!\n');
  process.exit(0);
}
