#!/usr/bin/env python3
"""
交互式需求查看组件生成器 - 基于 prd-data.json 生成可嵌入原型工程的 Vue 组件
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path


def load_prd_data(prd_json_path):
    """加载 PRD 结构化数据"""
    with open(prd_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_requirement_data_js(prd_data):
    """生成 requirement-data.js — PRD 数据的 JS 模块导出"""
    return f"""/**
 * 需求说明数据 - 由 proto-to-prd 自动生成
 * 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * 请勿手动修改，如需更新请重新运行 proto-to-prd 技能
 */

export const prdData = {json.dumps(prd_data, ensure_ascii=False, indent=2)};

export const prdMeta = {{
  generatedAt: "{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
  version: "1.0.0",
  source: "proto-to-prd"
}};
"""


def generate_viewer_component(prd_data):
    """生成 RequirementViewer.vue — 需求查看主组件基础骨架

    注意：本脚本生成的是基础骨架版本。生成后，AI 必须按照 SKILL.md 步骤8
    的「对照查阅交互设计」规范进行手动增强，补充以下特性：
    - 统一的 __panel 容器（flexbox 布局：sidebar + resize-handle + content）
    - 可拖拽调整宽度（resize handle，范围 200-500px）
    - 菜单树与原型侧边栏一级分组对齐（从 routeMappings.menuTree 读取）
    - 路由联动（useRoute 监听，自动展开/定位）
    - 隐藏页面展示（子页面嵌套在父页面下）
    - 增强字段卡片（按字段类型展示完整规则维度）
    - 关联功能点标签（⬅前置/➡后置）
    - 产品决策展示
    - 优先级标签（P0/P1/P2）
    """
    
    # 检测 Vue 版本
    vue_version = prd_data.get('meta', {}).get('vueVersion', 'vue3')
    is_vue3 = vue_version != 'vue2'
    
    # 检测 routeMappings（从数据中读取，避免硬编码）
    route_mappings = prd_data.get('routeMappings', {})
    menu_tree = route_mappings.get('menuTree', [])
    has_route_mappings = bool(route_mappings.get('routeToPageId'))
    
    # 构建菜单树数据注入（如果 prd-data.json 有 routeMappings）
    menu_tree_js = json.dumps(menu_tree, ensure_ascii=False, indent=2) if menu_tree else '[]'
    route_to_page_id_js = json.dumps(route_mappings.get('routeToPageId', {}), ensure_ascii=False) if has_route_mappings else '{}'
    hidden_prefix_js = json.dumps(route_mappings.get('hiddenRoutePrefixMap', []), ensure_ascii=False) if route_mappings.get('hiddenRoutePrefixMap') else '[]'
    
    component_template = f"""<template>
  <div class="requirement-viewer" :class="{{ 'is-open': visible }}">
    <!-- 切换按钮 -->
    <div class="requirement-viewer__trigger" :style="{{ right: visible ? totalPanelWidth + 'px' : '0px' }}" @click="visible = !visible" :title="visible ? '关闭需求说明' : '查看需求说明'">
      <span class="trigger-icon">📋</span>
    </div>

    <!-- 面板容器（sidebar + resize-handle + content 统一在右，flexbox布局） -->
    <div class="requirement-viewer__panel" :style="{{ width: totalPanelWidth + 'px', right: visible ? '0px' : (-totalPanelWidth) + 'px' }}">
      <!-- 侧边栏：菜单树 -->
      <div class="requirement-viewer__sidebar" :style="{{ width: sidebarWidth + 'px' }}">
        <div class="sidebar-header">
          <h3>需求说明</h3>
          <button class="close-btn" @click="visible = false">✕</button>
        </div>

        <!-- 当前路由标签 -->
        <div class="sidebar-current" v-if="currentRouteLabel">
          <span class="current-dot"></span>
          <span>当前：{{ currentRouteLabel }}</span>
        </div>

        <!-- 搜索 -->
        <div class="sidebar-search">
          <input v-model="searchKeyword" placeholder="搜索功能点..." class="search-input" />
        </div>

        <!-- 菜单树（与原型侧边栏一级分组对齐） -->
        <div class="sidebar-nav">
          <div v-for="group in filteredMenuTree" :key="group.label" class="nav-group">
            <div
              class="nav-group-title"
              :class="{{ active: group._active, 'has-current': group._hasCurrent }}"
              @click="toggleGroup(group)"
            >
              <span class="nav-group-icon">{{ group.icon }}</span>
              <span class="nav-group-label">{{ group.label }}</span>
              <span class="nav-group-arrow" :class="{{ expanded: group._expanded }}">▾</span>
            </div>

            <div v-show="group._expanded" class="nav-sub-items">
              <div v-for="page in group.pages" :key="page.id" class="nav-page-group">
                <div
                  class="nav-page-title"
                  :class="{{ active: activePage === page.id, 'is-current-route': page._isCurrentRoute }}"
                  @click="selectPage(page)"
                >
                  <span class="nav-page-dot" :class="{{ current: page._isCurrentRoute }}"></span>
                  <span class="nav-page-name">{{ page.name }}</span>
                  <span class="nav-page-route">{{ page.route }}</span>
                </div>

                <div v-if="activePage === page.id" class="nav-functions">
                  <div
                    v-for="func in page.functions"
                    :key="func.id"
                    class="nav-function"
                    :class="{{ active: activeFunction === func.id }}"
                    @click="activeFunction = func.id"
                  >
                    <span class="confidence" :class="func.confidence">●</span>
                    <span>{{ func.name }}</span>
                    <span class="func-priority" :class="func.priority">{{ func.priority }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 拖拽手柄 -->
      <div
        class="requirement-viewer__resize-handle"
        @mousedown="startResize"
      ></div>

      <!-- 内容区 -->
      <div class="requirement-viewer__content" :style="{{ width: contentWidth + 'px' }}" v-if="activeFunctionData">
        <div class="content-header">
          <h2>{{ activeFunctionData.name }}</h2>
          <span class="content-badge" :class="activeFunctionData.confidence">
            {{ confidenceLabel(activeFunctionData.confidence) }}
          </span>
          <span class="content-priority" :class="activeFunctionData.priority">{{ activeFunctionData.priority }}</span>
        </div>

        <div class="content-page-ref" v-if="activeFunctionPage">
          📄 {{ activeFunctionPage.name }} <code>{{ activeFunctionPage.route }}</code>
        </div>

        <!-- 关联功能点 -->
        <div class="content-section" v-if="activeFunctionData.relatedFunctions?.length">
          <h4>关联功能点</h4>
          <div class="related-funcs">
            <span v-for="(rf, i) in activeFunctionData.relatedFunctions" :key="i" class="related-tag" :class="rf.relation">
              {{ rf.relation === 'before' ? '⬅ 前置' : '➡ 后置' }}：{{ rf.name }}
              <span class="related-desc" v-if="rf.note">（{{ rf.note }}）</span>
            </span>
          </div>
        </div>

        <!-- 功能概述 -->
        <div class="content-section">
          <h4>功能概述</h4>
          <p>{{ activeFunctionData.description }}</p>
        </div>

        <!-- 产品决策 -->
        <div class="content-section" v-if="activeFunctionData.productDecisions?.length">
          <h4>产品决策</h4>
          <ul class="decision-list">
            <li v-for="(d, i) in activeFunctionData.productDecisions" :key="i">{{ d }}</li>
          </ul>
        </div>

        <!-- 基本事件流 -->
        <div class="content-section" v-if="activeFunctionData.flows?.main?.length">
          <h4>基本事件流</h4>
          <div class="flow-steps">
            <div v-for="(step, idx) in activeFunctionData.flows.main" :key="idx" class="flow-step">
              <span class="step-num">{{ idx + 1 }}</span>
              <span class="step-actor">{{ step.actor }}</span>
              <span class="step-action">{{ step.action }}</span>
            </div>
          </div>
        </div>

        <!-- 备选事件流 -->
        <div class="content-section" v-if="activeFunctionData.flows?.alternative?.length">
          <h4>备选事件流</h4>
          <div v-for="alt in activeFunctionData.flows.alternative" :key="alt.id" class="alt-flow">
            <div class="alt-trigger">{{ alt.condition }}</div>
            <div class="alt-steps">
              <span v-for="(s, i) in alt.steps" :key="i">{{ s }}；</span>
            </div>
          </div>
        </div>

        <!-- 异常事件流 -->
        <div class="content-section" v-if="activeFunctionData.flows?.exception?.length">
          <h4>异常事件流</h4>
          <div v-for="exc in activeFunctionData.flows.exception" :key="exc.id" class="exc-flow">
            <div class="exc-condition">⚠️ {{ exc.condition }}</div>
            <div class="exc-handling">处理：{{ exc.handling }}</div>
            <div class="exc-recovery">恢复：{{ exc.recovery }}</div>
          </div>
        </div>

        <!-- 需求规则 -->
        <div class="content-section" v-if="activeFunctionData.rules?.length">
          <h4>需求规则</h4>
          <table class="data-table">
            <thead><tr><th>规则</th><th>类型</th><th>说明</th></tr></thead>
            <tbody>
              <tr v-for="rule in activeFunctionData.rules" :key="rule.id">
                <td>{{ rule.id }}</td>
                <td>{{ rule.type }}</td>
                <td>{{ rule.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 字段说明（增强卡片形式） -->
        <div class="content-section" v-if="activeFunctionData.fields?.length">
          <h4>字段说明</h4>
          <div class="fields-detailed">
            <div v-for="field in activeFunctionData.fields" :key="field.name" class="field-card">
              <div class="field-card-header">
                <code class="field-name">{{ field.name }}</code>
                <span class="field-label">{{ field.label }}</span>
                <span class="field-type-tag">{{ field.type }}</span>
                <span class="field-required" :class="{{ required: field.required }}">{{ field.required ? '必填' : '选填' }}</span>
              </div>
              <table class="data-table field-detail-table" v-if="field.uiType || field.maxLength || field.format || field.options?.length || field.defaultValue || field.placeholder || field.validation || field.editable !== undefined || field.unique !== undefined">
                <tbody>
                  <tr v-if="field.uiType"><td class="fl">控件类型</td><td>{{ field.uiType }}</td></tr>
                  <tr v-if="field.maxLength"><td class="fl">长度限制</td><td>{{ field.maxLength }}</td></tr>
                  <tr v-if="field.format"><td class="fl">输入格式</td><td>{{ field.format }}</td></tr>
                  <tr v-if="field.options?.length"><td class="fl">可选值</td><td>{{ field.options.join(' / ') }}</td></tr>
                  <tr v-if="field.defaultValue"><td class="fl">默认值</td><td>{{ field.defaultValue }}</td></tr>
                  <tr v-if="field.placeholder"><td class="fl">占位提示</td><td>{{ field.placeholder }}</td></tr>
                  <tr v-if="field.multiple !== undefined"><td class="fl">多选</td><td>{{ field.multiple ? '是' : '否' }}</td></tr>
                  <tr v-if="field.resizable !== undefined"><td class="fl">可拉宽</td><td>{{ field.resizable ? '是' : '否' }}</td></tr>
                  <tr v-if="field.editable !== undefined"><td class="fl">可编辑</td><td>{{ field.editable ? '是' : '否' }}{{ field.editCondition ? '（' + field.editCondition + '）' : '' }}</td></tr>
                  <tr v-if="field.unique !== undefined"><td class="fl">数据唯一性</td><td>{{ field.unique ? '是' + (field.uniqueScope ? '（' + field.uniqueScope + '）' : '') : '否' }}</td></tr>
                  <tr v-if="field.validation"><td class="fl">校验规则</td><td>{{ field.validation }}</td></tr>
                  <tr v-if="field.validationTrigger"><td class="fl">校验触点</td><td>{{ field.validationTrigger }}</td></tr>
                  <tr v-if="field.validationMsg"><td class="fl">验证提示</td><td>{{ field.validationMsg }}</td></tr>
                  <tr v-if="field.autoFill"><td class="fl">自动取值</td><td>{{ field.autoFill }}</td></tr>
                  <tr v-if="field.hidden"><td class="fl">隐藏字段</td><td>是（取值逻辑：{{ field.hidden }}）</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 代码溯源 -->
        <div class="content-section">
          <h4>代码溯源</h4>
          <div class="code-trace">
            <div v-for="trace in activeFunctionData.codeTraces" :key="trace.file" class="trace-item">
              <span class="trace-file">{{ trace.file }}</span>
              <span v-if="trace.lines" class="trace-lines">L{{ trace.lines }}</span>
              <span class="trace-type">{{ trace.type }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="requirement-viewer__content requirement-viewer__empty" :style="{{ width: contentWidth + 'px' }}" v-else>
        <div class="empty-state">
          <span class="empty-icon">📋</span>
          <p>请从左侧选择功能点查看需求说明</p>
          <p class="empty-hint">需求面板菜单已与系统侧边栏对齐，切换路由时将自动联动</p>
          <p class="empty-hint">拖拽中间分隔线可调整面板宽度</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script{" setup" if is_vue3 else ""}>
{'import { ref, computed, watch, onBeforeUnmount } from "vue"' if is_vue3 else ''}
{'import { useRoute } from "vue-router"' if is_vue3 else ''}
{'import { prdData } from "./requirement-data.js"' if is_vue3 else 'import { prdData } from "./requirement-data"'}

{"const" if is_vue3 else "data() { return {"} route = {"useRoute()" if is_vue3 else "null"}
{"const" if is_vue3 else ""} visible = ref(false)
{"const" if is_vue3 else ""} searchKeyword = ref("")
{"const" if is_vue3 else ""} activePage = ref(null)
{"const" if is_vue3 else ""} activeFunction = ref(null)

// ===== 可拖拽宽度调整 =====
{"const" if is_vue3 else ""} sidebarWidth = ref(300)
{"const" if is_vue3 else ""} contentWidth = ref(380)
{"const" if is_vue3 else ""} HANDLE_WIDTH = 6
{"const" if is_vue3 else ""} MIN_SIDEBAR = 200
{"const" if is_vue3 else ""} MAX_SIDEBAR = 500
{"const" if is_vue3 else ""} MIN_CONTENT = 280

{"const" if is_vue3 else ""} totalPanelWidth = computed(() => sidebarWidth.value + HANDLE_WIDTH + contentWidth.value)
{"const" if is_vue3 else ""} isResizing = ref(false)
{"let" if is_vue3 else ""} resizeStartTotal = 0

{"function" if is_vue3 else ""} startResize(e) {{
  isResizing.value = true
  resizeStartTotal = totalPanelWidth.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
  e.preventDefault()
}}

{"function" if is_vue3 else ""} onResize(e) {{
  if (!isResizing.value) return
  const panelLeft = window.innerWidth - resizeStartTotal
  const newSidebar = e.clientX - panelLeft
  if (newSidebar >= MIN_SIDEBAR && newSidebar <= MAX_SIDEBAR) {{
    const newContent = resizeStartTotal - newSidebar - HANDLE_WIDTH
    if (newContent >= MIN_CONTENT) {{
      sidebarWidth.value = newSidebar
      contentWidth.value = newContent
    }}
  }}
}}

{"function" if is_vue3 else ""} stopResize() {{
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}}

{"onBeforeUnmount(() => {{" if is_vue3 else ""}
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
{"" if is_vue3 else ""}}}{"})" if is_vue3 else ""}

// ===== 路由映射（从 prdData.routeMappings 读取，避免硬编码） =====
{"const" if is_vue3 else ""} routeToPageId = {route_to_page_id_js}
{"const" if is_vue3 else ""} hiddenRoutePrefixMap = {hidden_prefix_js}
{"const" if is_vue3 else ""} menuTreeData = {menu_tree_js}

// ===== 构建菜单树 =====
{"const" if is_vue3 else ""} menuTree = ref([])

{"function" if is_vue3 else ""} buildMenuTree() {{
  if (menuTreeData.length > 0) {{
    // 从 routeMappings 读取菜单树结构
    return menuTreeData.map(group => ({{
      label: group.label,
      icon: group.icon,
      pages: (group.pageIds || []).map(pid => buildPageEntry(pid, (group.childMappings || {{}})[pid] || [])).filter(Boolean),
      _expanded: true,
      _active: false,
      _hasCurrent: false,
    }}))
  }}
  // 回退：直接从 pages 数组构建扁平菜单树
  return [{{
    label: '全部页面',
    icon: '📄',
    pages: (prdData.pages || []).map(p => ({{
      ...p,
      _isCurrentRoute: false,
      _childPages: [],
    }})),
    _expanded: true,
    _active: false,
    _hasCurrent: false,
  }}]
}}

{"function" if is_vue3 else ""} findPage(pageId) {{
  return prdData.pages?.find(p => p.id === pageId)
}}

{"function" if is_vue3 else ""} buildPageEntry(pageId, childPageIds) {{
  const page = findPage(pageId)
  if (!page) return null
  const entry = {{
    ...page,
    _isCurrentRoute: false,
    _childPages: [],
  }}
  for (const cid of (childPageIds || [])) {{
    const childPage = findPage(cid)
    if (childPage) {{
      entry._childPages.push({{
        ...childPage,
        _isCurrentRoute: false,
        _isChild: true,
      }})
    }}
  }}
  return entry
}}

// 初始化菜单树
menuTree.value = buildMenuTree()

// ===== 路由联动 =====
{"const" if is_vue3 else ""} currentRouteLabel = computed(() => {{
  const pageId = findPageIdByRoute({("route.path" if is_vue3 else "this.$route.path")})
  if (pageId) {{
    const page = findPage(pageId)
    return page ? page.name : null
  }}
  return null
}})

{"function" if is_vue3 else ""} findPageIdByRoute(path) {{
  if (routeToPageId[path]) return routeToPageId[path]
  for (const item of hiddenRoutePrefixMap) {{
    if (path.startsWith(item.prefix)) return item.pageId
  }}
  return null
}}

{"const" if is_vue3 else ""} activeFunctionPage = computed(() => {{
  if (!activeFunction.value) return null
  for (const page of prdData.pages || []) {{
    if (page.functions?.some(f => f.id === activeFunction.value)) return page
  }}
  return null
}})

{"const" if is_vue3 else ""} activeFunctionData = computed(() => {{
  if (!activeFunction.value) return null
  for (const page of prdData.pages || []) {{
    const func = page.functions?.find(f => f.id === activeFunction.value)
    if (func) return func
  }}
  return null
}})

// 路由联动监听
{'''watch(() => route.path, (newPath) => {
  if (!visible.value) return
  autoLocateByRoute(newPath)
})

watch(visible, (val) => {
  if (val) {
    autoLocateByRoute(route.path)
  }
})''' if is_vue3 else '''watch: {
  '$route.path': function(newPath) {
    if (!visible) return
    autoLocateByRoute(newPath)
  }
}'''}

{"function" if is_vue3 else ""} autoLocateByRoute(path) {{
  const pageId = findPageIdByRoute(path)
  if (!pageId) return

  for (const group of menuTree.value) {{
    group._hasCurrent = false
    for (const page of group.pages) {{
      page._isCurrentRoute = false
      for (const child of (page._childPages || [])) {{
        child._isCurrentRoute = false
      }}
    }}
  }}

  for (const group of menuTree.value) {{
    for (const page of group.pages) {{
      if (page.id === pageId) {{
        page._isCurrentRoute = true
        group._hasCurrent = true
        group._expanded = true
        activePage.value = page.id
        if (page.functions?.length > 0) {{
          activeFunction.value = page.functions[0].id
        }}
        return
      }}
      for (const child of (page._childPages || [])) {{
        if (child.id === pageId) {{
          child._isCurrentRoute = true
          page._isCurrentRoute = true
          group._hasCurrent = true
          group._expanded = true
          activePage.value = page.id
          if (child.functions?.length > 0) {{
            activeFunction.value = child.functions[0].id
          }}
          return
        }}
      }}
    }}
  }}
}}

// ===== 交互操作 =====
{"function" if is_vue3 else ""} toggleGroup(group) {{
  group._expanded = !group._expanded
}}

{"function" if is_vue3 else ""} selectPage(page) {{
  if (activePage.value === page.id) {{
    activePage.value = null
  }} else {{
    activePage.value = page.id
    if (page.functions?.length > 0) {{
      activeFunction.value = page.functions[0].id
    }}
  }}
}}

// 搜索过滤
{"const" if is_vue3 else ""} filteredMenuTree = computed(() => {{
  if (!searchKeyword.value) return menuTree.value
  const keyword = searchKeyword.value.toLowerCase()
  return menuTree.value.map(group => {{
    const filteredPages = group.pages.filter(page => {{
      const pageMatch = page.name.toLowerCase().includes(keyword) ||
        page.route.toLowerCase().includes(keyword)
      const funcMatch = page.functions?.some(f =>
        f.name.toLowerCase().includes(keyword) ||
        f.description?.toLowerCase().includes(keyword)
      )
      return pageMatch || funcMatch
    }})
    return {{
      ...group,
      pages: filteredPages,
      _expanded: filteredPages.length > 0,
    }}
  }}).filter(group => group.pages.length > 0)
}})

{"function" if is_vue3 else ""} confidenceLabel(level) {{
  const labels = {{ high: '高置信度', medium: '中置信度', low: '低置信度' }}
  return labels[level] || level
}}
{"" if is_vue3 else "} }"}
</script>

<style scoped>
.requirement-viewer {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  color: #333;
}}

.requirement-viewer__trigger {{
  position: fixed;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 80px;
  background: #409eff;
  border-radius: 8px 0 0 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  z-index: 10000;
  box-shadow: -2px 0 8px rgba(0,0,0,0.15);
}}
.requirement-viewer__trigger:hover {{ background: #66b1ff; }}
.trigger-icon {{ font-size: 18px; }}

/* ===== 面板容器：sidebar + handle + content ===== */
.requirement-viewer__panel {{
  position: fixed;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: row;
  z-index: 9999;
  transition: right 0.3s;
  box-shadow: -4px 0 12px rgba(0,0,0,0.1);
}}

/* ===== 侧边栏 ===== */
.requirement-viewer__sidebar {{
  height: 100vh;
  background: #fff;
  border-left: 1px solid #e4e7ed;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}}

.sidebar-header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;
}}
.sidebar-header h3 {{ margin: 0; font-size: 16px; }}
.close-btn {{ background: none; border: none; font-size: 18px; cursor: pointer; color: #999; }}
.close-btn:hover {{ color: #333; }}

.sidebar-current {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #f0f9ff;
  border-bottom: 1px solid #d0e8ff;
  font-size: 12px;
  color: #409eff;
  flex-shrink: 0;
}}
.current-dot {{
  width: 8px; height: 8px;
  border-radius: 50%;
  background: #409eff;
  animation: pulse 1.5s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.4; }}
}}

.sidebar-search {{ padding: 10px 16px; border-bottom: 1px solid #f0f0f0; flex-shrink: 0; }}
.search-input {{
  width: 100%;
  padding: 7px 10px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  outline: none;
  font-size: 13px;
}}
.search-input:focus {{ border-color: #409eff; }}

/* ===== 菜单树 ===== */
.sidebar-nav {{ flex: 1; overflow-y: auto; }}

.nav-group {{ margin-bottom: 0; border-bottom: 1px solid #f5f5f5; }}

.nav-group-title {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  background: #fafbfc;
  transition: background 0.2s;
  user-select: none;
}}
.nav-group-title:hover {{ background: #f0f2f5; }}
.nav-group-title.active {{ color: #409eff; background: #ecf5ff; }}
.nav-group-title.has-current {{ color: #409eff; }}
.nav-group-icon {{ font-size: 14px; flex-shrink: 0; }}
.nav-group-label {{ flex: 1; }}
.nav-group-arrow {{
  font-size: 10px;
  color: #c0c4cc;
  transition: transform 0.2s;
}}
.nav-group-arrow.expanded {{ transform: rotate(-180deg); }}

.nav-sub-items {{ padding: 2px 0; }}

.nav-page-group {{ }}

.nav-page-title {{
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px 8px 32px;
  cursor: pointer;
  font-size: 13px;
  color: #333;
  transition: background 0.15s;
}}
.nav-page-title:hover {{ background: #f5f7fa; }}
.nav-page-title.active {{ background: #ecf5ff; color: #409eff; }}
.nav-page-title.is-current-route {{ font-weight: 600; }}

.nav-page-dot {{
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #dcdfe6;
  flex-shrink: 0;
}}
.nav-page-dot.current {{ background: #409eff; }}

.nav-page-name {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.nav-page-route {{ font-size: 10px; color: #c0c4cc; flex-shrink: 0; }}

.nav-functions {{ padding-left: 16px; border-left: 2px solid #ecf5ff; margin-left: 28px; }}
.nav-function {{
  padding: 7px 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  transition: background 0.15s;
  border-radius: 4px;
}}
.nav-function:hover {{ background: #f5f7fa; }}
.nav-function.active {{ background: #ecf5ff; color: #409eff; font-weight: 500; }}
.confidence {{ font-size: 10px; }}
.confidence.high {{ color: #67c23a; }}
.confidence.medium {{ color: #e6a23c; }}
.confidence.low {{ color: #f56c6c; }}
.func-priority {{
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: auto;
}}
.func-priority.P0 {{ background: #fef0f0; color: #f56c6c; }}
.func-priority.P1 {{ background: #fdf6ec; color: #e6a23c; }}
.func-priority.P2 {{ background: #f0f9eb; color: #67c23a; }}

/* ===== 拖拽手柄 ===== */
.requirement-viewer__resize-handle {{
  width: 6px;
  height: 100vh;
  flex-shrink: 0;
  cursor: col-resize;
  z-index: 1;
  position: relative;
  background: transparent;
  transition: background 0.2s;
}}
.requirement-viewer__resize-handle:hover {{
  background: rgba(64, 158, 255, 0.15);
}}
.requirement-viewer__resize-handle::after {{
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 40px;
  border-radius: 2px;
  background: #dcdfe6;
  transition: all 0.2s;
}}
.requirement-viewer__resize-handle:hover::after {{
  background: #409eff;
  height: 60px;
}}

/* ===== 内容区 ===== */
.requirement-viewer__content {{
  height: 100vh;
  background: #fafbfc;
  overflow-y: auto;
  padding: 20px;
  flex-shrink: 0;
}}

.content-header {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}}
.content-header h2 {{ margin: 0; font-size: 16px; }}
.content-badge {{
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
}}
.content-badge.high {{ background: #f0f9eb; color: #67c23a; }}
.content-badge.medium {{ background: #fdf6ec; color: #e6a23c; }}
.content-badge.low {{ background: #fef0f0; color: #f56c6c; }}
.content-priority {{
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  background: #f0f0f0;
  color: #909399;
}}

.content-page-ref {{
  font-size: 12px;
  color: #909399;
  margin-bottom: 16px;
  padding: 6px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}}
.content-page-ref code {{ color: #409eff; font-size: 11px; }}

.related-funcs {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.related-tag {{
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}}
.related-tag.before {{ background: #fdf6ec; color: #e6a23c; border: 1px solid #f5dab1; }}
.related-tag.after {{ background: #ecf5ff; color: #409eff; border: 1px solid #d0e8ff; }}
.related-desc {{ color: #909399; font-size: 10px; }}

.content-section {{ margin-bottom: 18px; }}
.content-section h4 {{
  font-size: 13px;
  color: #606266;
  margin: 0 0 8px 0;
  padding-bottom: 4px;
  border-bottom: 1px solid #ebeef5;
}}

.decision-list {{ padding-left: 16px; margin: 0; font-size: 13px; color: #666; }}
.decision-list li {{ margin-bottom: 4px; }}

.flow-steps {{ padding-left: 8px; }}
.flow-step {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 12px;
}}
.step-num {{
  width: 20px; height: 20px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  flex-shrink: 0;
}}
.step-actor {{ color: #909399; min-width: 28px; font-size: 11px; }}
.step-action {{ color: #333; }}

.data-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
}}
.data-table th {{
  background: #f5f7fa;
  padding: 5px 7px;
  text-align: left;
  border: 1px solid #ebeef5;
  color: #909399;
  font-weight: normal;
}}
.data-table td {{
  padding: 5px 7px;
  border: 1px solid #ebeef5;
}}
.field-name {{ font-family: monospace; color: #409eff; }}

.fields-detailed {{ display: flex; flex-direction: column; gap: 8px; }}
.field-card {{
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px;
}}
.field-card-header {{
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}}
.field-card-header .field-name {{
  font-size: 12px;
  padding: 1px 6px;
  background: #f0f7ff;
  border-radius: 3px;
}}
.field-label {{ font-size: 12px; font-weight: 500; color: #303133; }}
.field-type-tag {{
  font-size: 10px;
  padding: 1px 6px;
  background: #f5f7fa;
  border-radius: 3px;
  color: #909399;
}}
.field-required {{
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #f5f7fa;
  color: #909399;
}}
.field-required.required {{ background: #fef0f0; color: #f56c6c; }}
.field-detail-table {{ margin-top: 4px; }}
.field-detail-table td {{ font-size: 11px; }}
.field-detail-table td.fl {{ color: #909399; width: 80px; white-space: nowrap; }}

.code-trace {{ padding-left: 4px; }}
.trace-item {{
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  font-size: 11px;
}}
.trace-file {{ font-family: monospace; color: #409eff; }}
.trace-lines {{ color: #909399; font-size: 10px; }}
.trace-type {{ color: #67c23a; font-size: 10px; background: #f0f9eb; padding: 1px 5px; border-radius: 3px; }}

.alt-flow, .exc-flow {{ padding: 8px; margin-bottom: 8px; border-radius: 4px; font-size: 12px; }}
.alt-flow {{ background: #fdf6ec; }}
.exc-flow {{ background: #fef0f0; }}
.alt-trigger, .exc-condition {{ font-weight: 500; margin-bottom: 4px; }}
.exc-handling, .exc-recovery, .alt-steps {{ font-size: 12px; color: #666; }}

.empty-state {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  color: #c0c4cc;
}}
.empty-icon {{ font-size: 48px; margin-bottom: 12px; }}
.empty-hint {{ font-size: 12px; margin-top: 8px; }}
</style>
"""
    return component_template


def generate_router_inject(prd_data):
    """生成 router-inject.js — 路由注入脚本"""
    vue_version = prd_data.get('meta', {}).get('vueVersion', 'vue3')
    
    return f"""/**
 * 路由注入脚本 - 将需求查看组件注入到原型工程路由
 * 使用方式：在路由配置文件中 import 本模块并执行 inject(requirementRoutes)
 * 
 * Vue 版本: {vue_version}
 */

import RequirementViewer from './RequirementViewer.vue'

/**
 * 将需求查看路由注入到现有路由配置
 * @param {{Array}} routes - 现有路由配置数组
 * @param {{Object}} options - 配置选项
 * @param {{string}} options.path - 需求查看路由路径（默认: /requirement-viewer）
 * @param {{string}} options.mode - 路由模式（hash/history）
 * @returns {{Array}} 注入后的路由配置
 */
export function inject(routes, options = {{}}) {{
  const viewerPath = options.path || '/requirement-viewer'
  
  // 添加全局需求查看路由
  routes.push({{
    path: viewerPath,
    name: 'RequirementViewer',
    component: RequirementViewer,
    meta: {{ title: '需求说明', hidden: true }}
  }})
  
  return routes
}}

/**
 * 为每个页面路由添加需求入口
 * 在每个路由的 meta 中添加 requirementData 引用
 * @param {{Array}} routes - 路由配置
 * @param {{Object}} pageRequirementMap - 页面到需求ID的映射
 * @returns {{Array}} 增强后的路由配置
 */
export function addRequirementMeta(routes, pageRequirementMap = {{}}) {{
  return routes.map(route => {{
    const reqIds = pageRequirementMap[route.path]
    if (reqIds) {{
      route.meta = {{
        ...route.meta,
        requirementIds: reqIds
      }}
    }}
    return route
  }})
}}
"""


def generate_install_script():
    """生成 install.sh — 一键集成脚本"""
    return """#!/bin/bash
# proto-to-prd 需求查看组件 - 一键集成脚本
# 使用方式: bash install.sh <目标工程目录>

set -e

TARGET_DIR=${1:-.}
VIEWER_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo " proto-to-prd 需求查看组件 - 集成安装"
echo "========================================="
echo ""
echo "目标工程: $TARGET_DIR"
echo "组件目录: $VIEWER_DIR"
echo ""

# 检查目标目录
if [ ! -d "$TARGET_DIR/src" ]; then
  echo "⚠️  未找到 src 目录，请确认目标工程路径"
  exit 1
fi

# 创建目标目录
INSTALL_DIR="$TARGET_DIR/src/requirement-viewer"
mkdir -p "$INSTALL_DIR"

# 复制组件文件
echo "📦 复制组件文件..."
cp "$VIEWER_DIR/RequirementViewer.vue" "$INSTALL_DIR/"
cp "$VIEWER_DIR/requirement-data.js" "$INSTALL_DIR/"
cp "$VIEWER_DIR/router-inject.js" "$INSTALL_DIR/"

echo "✅ 组件文件已复制到 $INSTALL_DIR"
echo ""
echo "📝 接下来请手动完成以下步骤："
echo ""
echo "1. 在路由配置文件中引入注入脚本："
echo "   import {{ inject }} from '@/requirement-viewer/router-inject'"
echo ""
echo "2. 在路由配置中使用注入："
echo "   const routes = inject(yourRoutes)"
echo ""
echo "3. 在 App.vue 中添加全局需求查看入口："
echo "   <RequirementViewer />"
echo "   import RequirementViewer from '@/requirement-viewer/RequirementViewer.vue'"
echo ""
echo "========================================="
echo " 安装完成！"
echo "========================================="
"""


def generate_install_ps1():
    """生成 install.ps1 — Windows 环境一键集成脚本"""
    return """# proto-to-prd 需求查看组件 - 一键集成脚本 (Windows PowerShell)
# 使用方式: .\\install.ps1 -TargetDir <目标工程目录>

param(
    [string]$TargetDir = "."
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " proto-to-prd 需求查看组件 - 集成安装" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "目标工程: $TargetDir"
Write-Host "组件目录: $PSScriptRoot"
Write-Host ""

# 检查目标目录
if (-not (Test-Path "$TargetDir\\src")) {
    Write-Host "⚠️  未找到 src 目录，请确认目标工程路径" -ForegroundColor Yellow
    exit 1
}

# 创建目标目录
$InstallDir = "$TargetDir\\src\\requirement-viewer"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

# 复制组件文件
Write-Host "📦 复制组件文件..." -ForegroundColor Green
Copy-Item "$PSScriptRoot\\RequirementViewer.vue" -Destination "$InstallDir\\" -Force
Copy-Item "$PSScriptRoot\\requirement-data.js" -Destination "$InstallDir\\" -Force
Copy-Item "$PSScriptRoot\\router-inject.js" -Destination "$InstallDir\\" -Force

Write-Host "✅ 组件文件已复制到 $InstallDir" -ForegroundColor Green
Write-Host ""
Write-Host "📝 接下来请手动完成以下步骤：" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. 在路由配置文件中引入注入脚本："
Write-Host "   import { inject } from '@/requirement-viewer/router-inject'"
Write-Host ""
Write-Host "2. 在路由配置中使用注入："
Write-Host "   const routes = inject(yourRoutes)"
Write-Host ""
Write-Host "3. 在 App.vue 中添加全局需求查看入口："
Write-Host "   <RequirementViewer />"
Write-Host "   import RequirementViewer from '@/requirement-viewer/RequirementViewer.vue'"
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " 安装完成！" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
"""


def generate_viewer(prd_json_path, output_dir):
    """主函数：生成交互视图组件"""
    print(f"加载 PRD 数据: {prd_json_path}")
    prd_data = load_prd_data(prd_json_path)
    
    viewer_dir = os.path.join(output_dir, 'requirement-viewer')
    os.makedirs(viewer_dir, exist_ok=True)
    
    # 生成各文件
    files_to_generate = {
        'requirement-data.js': generate_requirement_data_js(prd_data),
        'RequirementViewer.vue': generate_viewer_component(prd_data),
        'router-inject.js': generate_router_inject(prd_data),
        'install.sh': generate_install_script(),
        'install.ps1': generate_install_ps1(),
    }
    
    for filename, content in files_to_generate.items():
        filepath = os.path.join(viewer_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  [OK] {filename}")
    
    # 给 install.sh 添加执行权限
    install_path = os.path.join(viewer_dir, 'install.sh')
    try:
        os.chmod(install_path, 0o755)
    except Exception:
        pass  # Windows 环境下 chmod 可能不可用
    
    print(f"\n交互视图组件已生成到: {viewer_dir}")
    print(f"共 5 个文件（含 Windows/Unix 双平台安装脚本）")
    print(f"请参考 install.sh / install.ps1 中的说明将组件集成到原型工程")
    print(f"\n注意：脚本生成的是基础骨架，AI 将在此基础上按 SKILL 规范进行增强。")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='交互式需求查看组件生成器')
    parser.add_argument('prd_json', help='PRD 结构化 JSON 文件路径')
    parser.add_argument('--output', default='outputs', help='输出目录（默认: outputs）')
    
    args = parser.parse_args()
    generate_viewer(args.prd_json, args.output)
