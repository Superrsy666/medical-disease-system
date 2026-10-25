<template>
  <router-view />
</template>

<style>
body {
  margin: 0;
  padding: 0;
  font-family: 'Microsoft YaHei', sans-serif;
}

/* ===== 全局基础：防止横向溢出 ===== */
html, body {
  width: 100%;
  overflow-x: hidden;
  -webkit-text-size-adjust: 100%;
}

/* ===== 全局移动端适配（<=768px 视为手机/窄屏） ===== */
@media (max-width: 768px) {
  .el-main { padding: 10px !important; }
  .page { padding: 12px !important; }
  .el-card__body { padding: 14px !important; }
  .el-dialog, .el-message-box { width: 92% !important; max-width: 92vw; }
  .el-drawer__body { padding: 0 !important; }

  h2 { font-size: 18px !important; }
  h3 { font-size: 16px !important; }

  /* 表单纵向排列，避免横向溢出 */
  .el-form-item {
    display: block;
    margin-right: 0 !important;
    margin-bottom: 16px;
  }
  .el-form-item__label {
    width: 100% !important;
    text-align: left;
    line-height: 1.6;
    padding: 0 0 4px;
  }
  .el-form-item__content {
    margin-left: 0 !important;
    width: 100%;
  }
  .el-input, .el-select, .el-date-editor,
  .el-input-number, .el-cascader { max-width: 100% !important; }

  /* 分页与搜索栏换行 */
  .el-pagination { flex-wrap: wrap; justify-content: center; }
  .el-pagination .el-pagination__total, .el-pagination__sizes { display: none; }

  /* 操作按钮组可换行 */
  .el-button-group, .el-form .el-button { margin-bottom: 4px; }
}
</style>
