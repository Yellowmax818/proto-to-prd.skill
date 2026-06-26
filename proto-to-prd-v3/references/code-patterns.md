# Vue/HTML 代码解析模式库

本文档记录从 Vue/HTML 代码中提取需求信息的通用模式，供 AI 在解析代码时参考。

## Vue SFC 解析模式

### 模板层（template）

| 代码模式 | 提取信息 | 映射到PRD |
|---------|---------|----------|
| `<router-link :to="...">` | 页面导航关系 | 核心业务流程、功能清单 |
| `<router-view />` | 页面嵌套关系 | 页面结构 |
| `v-if="condition"` | 条件渲染逻辑 | 备选事件流、需求规则 |
| `v-show="condition"` | 条件显示逻辑 | 备选事件流、需求规则 |
| `v-for="item in list"` | 列表数据源 | 数据需求说明、字段说明 |
| `v-model="form.field"` | 表单字段绑定 | 字段说明（字段名、绑定路径） |
| `@click="handler"` | 点击事件 | 基本事件流 |
| `@submit="handler"` | 提交事件 | 基本事件流 |
| `@change="handler"` | 变更事件 | 备选事件流 |
| `:rules="rules"` | 表单校验规则 | 需求规则（校验规则） |
| `:disabled="condition"` | 禁用条件 | 需求规则（权限/状态规则） |
| `v-loading="loading"` | 加载状态 | 异常事件流（异步等待） |
| `<el-dialog :visible.sync="dialogVisible">` | 弹窗控制 | 备选事件流 |
| `<el-table :data="tableData">` | 列表数据 | 数据需求说明 |
| `<el-form :model="formData">` | 表单数据 | 字段说明 |
| `<el-tab-pane>` | 标签页切换 | 核心业务流程、备选事件流 |
| `<el-steps>` | 步骤条 | 核心业务流程 |
| `v-auth="'permission'"` | 权限指令 | 安全需求（权限控制） |
| `v-permission` | 权限指令 | 安全需求（权限控制） |

### 脚本层（script）

| 代码模式 | 提取信息 | 映射到PRD |
|---------|---------|----------|
| `data() { return { ... } }` | 组件状态定义 | 字段说明（初始值、类型推断） |
| `props: { ... }` | 组件入参 | 字段说明 |
| `computed: { ... }` | 计算属性/业务规则 | 需求规则 |
| `methods: { ... }` | 方法/事件处理 | 基本事件流、备选事件流 |
| `watch: { ... }` | 监听/联动逻辑 | 备选事件流、需求规则 |
| `created() / mounted()` | 生命周期初始化逻辑 | 基本事件流（页面加载） |
| `axios.get/post(url, data)` | API调用 | 接口需求 |
| `this.$store.dispatch/get` | 状态管理交互 | 数据需求说明 |
| `this.$router.push/replace` | 路由跳转 | 基本事件流、核心业务流程 |
| `this.$message.success/error` | 消息提示 | 异常事件流、基本事件流 |
| `this.$confirm(...)` | 二次确认 | 基本事件流 |
| `import xxx from './components/xxx'` | 组件依赖 | 页面结构 |
| `export default { name: 'xxx' }` | 组件名称 | 页面结构 |

### 路由配置解析

```javascript
// router.js 常见模式
const routes = [
  {
    path: '/users',           // → 页面路由
    name: 'UserList',         // → 页面名称
    component: () => import('@/views/UserList.vue'),  // → 关联代码文件
    meta: { title: '用户管理', requiresAuth: true },   // → 页面标题、权限要求
    children: [...]           // → 页面层级关系
  }
]
```

提取要点：
- path → 路由路径
- name → 页面标识
- component → 关联文件
- meta.title → 页面中文名
- meta.requiresAuth → 权限需求
- children → 页面层级

### 表单校验规则解析

```javascript
rules: {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度2-20字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '仅限字母数字下划线', trigger: 'blur' }
  ]
}
```

提取要点：
- required → 必填
- min/max → 长度限制
- pattern → 格式校验
- message → 错误提示（异常事件流）
- trigger → 触发时机

## HTML 解析模式

| 代码模式 | 提取信息 | 映射到PRD |
|---------|---------|----------|
| `<form>` | 表单区域 | 字段说明 |
| `<input type="text/email/number/...">` | 输入类型 | 字段说明（类型） |
| `<input required>` | 必填字段 | 需求规则 |
| `<input pattern="...">` | 正则校验 | 需求规则 |
| `<select>` | 下拉选择 | 字段说明（枚举值） |
| `<button onclick="...">` | 按钮操作 | 基本事件流 |
| `<table>` | 数据表格 | 数据需求说明 |
| `<a href="...">` | 链接导航 | 核心业务流程 |
| `<div class="modal/dialog">` | 弹窗区域 | 备选事件流 |

## 产品决策推断模式

| 代码特征 | 推断的产品决策 | 置信度 |
|---------|--------------|--------|
| 提交成功后 `this.$router.push('/list')` | 提交后无需二次确认，直接跳转 | 🟢 |
| 删除操作无 `this.$confirm` | 删除无需确认（低风险）或遗漏确认（缺陷） | 🟡 |
| 表单 `:disabled="isEdit"` | 编辑模式下部分字段不可修改 | 🟢 |
| 列表默认 `sort: '-createTime'` | 最新数据优先展示 | 🟢 |
| `v-if="role === 'admin'"` | 管理员可见/可操作 | 🟢 |
| `v-if="status === 'draft'"` | 仅草稿状态可操作 | 🟢 |
| 接口返回后 `this.$message.error(msg)` | 统一错误提示机制 | 🟢 |
| `beforeDestroy` 中清理定时器 | 防止内存泄漏的技术决策 | 🔴（纯技术，非产品决策） |
