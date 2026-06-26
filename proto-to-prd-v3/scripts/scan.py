#!/usr/bin/env python3
"""
原型工程扫描器 - 递归扫描工程目录，提取文件清单、目录结构、代码指纹
"""

import os
import sys
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path


def compute_file_hash(filepath):
    """计算文件内容的 MD5 哈希"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None


def should_scan(filepath):
    """判断文件是否需要扫描"""
    ext = Path(filepath).suffix.lower()
    target_exts = {'.vue', '.html', '.htm', '.js', '.ts', '.jsx', '.tsx'}
    return ext in target_exts


def scan_directory(root_dir, output_dir):
    """扫描目录，生成文件清单和指纹"""
    root_path = Path(root_dir).resolve()
    
    if not root_path.exists():
        print(f"错误：目录不存在 - {root_dir}")
        sys.exit(1)
    
    files_info = []
    dir_tree = {}
    stats = {
        'vue': 0, 'html': 0, 'js': 0, 'ts': 0, 'other': 0,
        'total_lines': 0, 'total_files': 0
    }
    
    # 扫描文件
    for dirpath, dirnames, filenames in os.walk(root_path):
        # 跳过 node_modules, .git, dist 等目录
        dirnames[:] = [d for d in dirnames if d not in {
            'node_modules', '.git', 'dist', 'build', '.nuxt', '.next', 'coverage'
        }]
        
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == '.':
            rel_dir = ''
        
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_path)
            
            if not should_scan(filepath):
                continue
            
            file_hash = compute_file_hash(filepath)
            
            # 统计行数
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                line_count = 0
            
            ext = Path(filename).suffix.lower()
            file_category = {
                '.vue': 'vue', '.html': 'html', '.htm': 'html',
                '.js': 'js', '.jsx': 'js',
                '.ts': 'ts', '.tsx': 'ts'
            }.get(ext, 'other')
            
            stats[file_category] += 1
            stats['total_files'] += 1
            stats['total_lines'] += line_count
            
            files_info.append({
                'path': rel_path,
                'name': filename,
                'ext': ext,
                'category': file_category,
                'hash': file_hash,
                'lines': line_count,
                'size': os.path.getsize(filepath)
            })
    
    # 构建目录树
    def build_tree(path_prefix, depth=0):
        tree = {}
        for f in files_info:
            p = f['path']
            if p.startswith(path_prefix):
                remaining = p[len(path_prefix):].strip('/')
                parts = remaining.split('/')
                if len(parts) == 1:
                    tree[f['name']] = {
                        'type': 'file',
                        'category': f['category'],
                        'lines': f['lines']
                    }
        return tree
    
    # 读取旧指纹（增量模式）
    fingerprint_path = os.path.join(output_dir, 'fingerprint.json')
    old_fingerprint = {}
    is_incremental = False
    fingerprint_dir_issue = False
    
    # 检查 fingerprint.json 是否为目录（上次运行参数错误导致）
    if os.path.isdir(fingerprint_path):
        fingerprint_dir_issue = True
        print(f"⚠️  警告：fingerprint.json 是一个目录而非文件（可能由上次 --output 参数错误导致）")
        # 尝试查找备份指纹
        for backup_name in ['fingerprint_v2.json', 'fingerprint_backup.json']:
            backup_path = os.path.join(output_dir, backup_name)
            if os.path.isfile(backup_path):
                print(f"   找到备份指纹: {backup_name}，将使用备份")
                fingerprint_path = backup_path
                fingerprint_dir_issue = False
                break
        if fingerprint_dir_issue:
            print(f"   未找到备份指纹，将以全量模式运行")
    
    if os.path.isfile(fingerprint_path):
        try:
            with open(fingerprint_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                old_fingerprint = {item['path']: item['hash'] for item in old_data.get('files', [])}
                is_incremental = True
                if fingerprint_dir_issue:
                    print(f"   已从备份指纹读取 {len(old_fingerprint)} 个文件的指纹信息")
        except Exception as e:
            print(f"⚠️  读取指纹文件失败: {e}，将以全量模式运行")
            is_incremental = False
    
    # 计算变更
    changes = {
        'added': [],
        'modified': [],
        'deleted': [],
        'unchanged': []
    }
    
    new_fingerprint = {f['path']: f['hash'] for f in files_info}
    
    if is_incremental:
        for path, hash_val in new_fingerprint.items():
            if path not in old_fingerprint:
                changes['added'].append(path)
            elif old_fingerprint[path] != hash_val:
                changes['modified'].append(path)
            else:
                changes['unchanged'].append(path)
        
        for path in old_fingerprint:
            if path not in new_fingerprint:
                changes['deleted'].append(path)
    
    # 生成路由配置检测
    router_files = []
    for f in files_info:
        name_lower = f['name'].lower()
        if 'router' in name_lower and f['category'] in ('js', 'ts'):
            router_files.append(f['path'])
    
    # 生成 package.json 信息
    package_info = {}
    package_json_path = os.path.join(root_dir, 'package.json')
    if os.path.exists(package_json_path):
        try:
            with open(package_json_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
                package_info = {
                    'name': pkg.get('name', ''),
                    'version': pkg.get('version', ''),
                    'dependencies': list(pkg.get('dependencies', {}).keys()),
                    'devDependencies': list(pkg.get('devDependencies', {}).keys()),
                }
                # 检测 Vue 版本
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                vue_version = deps.get('vue', deps.get('vue2', ''))
                if vue_version:
                    package_info['vueVersion'] = 'vue2' if vue_version.startswith('2') else 'vue3'
                # 检测 UI 库
                ui_libs = ['element-plus', 'element-ui', 'ant-design-vue', 'vant', 'naive-ui', 'arco-design-vue']
                detected_ui = [lib for lib in ui_libs if lib in deps]
                if detected_ui:
                    package_info['uiLibrary'] = detected_ui
        except Exception:
            pass
    
    # 输出结果
    result = {
        'scanTime': datetime.now().isoformat(),
        'rootDir': str(root_dir),
        'mode': 'incremental' if is_incremental else 'full',
        'packageInfo': package_info,
        'routerFiles': router_files,
        'stats': stats,
        'files': files_info,
        'changes': changes if is_incremental else None
    }
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 写入指纹前，确保 fingerprint.json 不是目录
    final_fingerprint_path = os.path.join(output_dir, 'fingerprint.json')
    if os.path.isdir(final_fingerprint_path):
        print(f"⚠️  尝试删除旧的 fingerprint.json 目录...")
        try:
            import shutil
            shutil.rmtree(final_fingerprint_path)
            print(f"   已删除旧的 fingerprint.json 目录")
        except Exception as e:
            print(f"   无法删除目录: {e}")
            # 使用备用文件名
            final_fingerprint_path = os.path.join(output_dir, 'fingerprint_v2.json')
            print(f"   将使用备用文件名: fingerprint_v2.json")
    
    # 保存指纹
    with open(final_fingerprint_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 打印摘要
    print(f"\n{'='*50}")
    print(f"扫描完成 - {'增量模式' if is_incremental else '全量模式'}")
    print(f"{'='*50}")
    print(f"目录: {root_dir}")
    print(f"文件统计: .vue({stats['vue']}) .html({stats['html']}) .js({stats['js']}) .ts({stats['ts']})")
    print(f"总文件数: {stats['total_files']}, 总行数: {stats['total_lines']}")
    
    if package_info.get('vueVersion'):
        print(f"Vue 版本: {package_info['vueVersion']}")
    if package_info.get('uiLibrary'):
        print(f"UI 库: {', '.join(package_info['uiLibrary'])}")
    if router_files:
        print(f"路由文件: {', '.join(router_files)}")
    
    if is_incremental:
        print(f"\n变更统计:")
        print(f"  新增: {len(changes['added'])}")
        print(f"  修改: {len(changes['modified'])}")
        print(f"  删除: {len(changes['deleted'])}")
        print(f"  未变: {len(changes['unchanged'])}")
    
    print(f"\n指纹文件已保存: {fingerprint_path}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='原型工程扫描器')
    parser.add_argument('root_dir', help='原型工程根目录')
    parser.add_argument('--output', default='outputs', help='输出目录（默认: outputs）')
    
    args = parser.parse_args()
    scan_directory(args.root_dir, args.output)
