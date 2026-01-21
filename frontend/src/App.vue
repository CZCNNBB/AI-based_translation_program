<template>
  <div class="common-layout">
    <el-container class="main-container">
      <el-aside width="200px" class="aside">
        <div class="logo">
          <el-icon :size="24" color="#409eff"><EditPen /></el-icon>
          <span>翻译引擎</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical"
          @select="handleSelect"
        >
          <el-menu-item index="text">
            <el-icon><Document /></el-icon>
            <span>单文本翻译</span>
          </el-menu-item>
          <el-menu-item index="batch">
            <el-icon><Files /></el-icon>
            <span>批量翻译</span>
          </el-menu-item>
          <el-menu-item index="settings">
            <el-icon><Setting /></el-icon>
            <span>设置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-container>
        <el-header class="header">
          <div class="header-title">
            {{ headerTitle }}
          </div>
        </el-header>

        <el-main class="main-content">
          <component :is="currentComponent" />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { EditPen, Document, Files } from "@element-plus/icons-vue";
import TextTranslation from "./components/TextTranslation.vue";
import BatchTranslation from "./components/BatchTranslation.vue";

const activeMenu = ref("text");

const currentComponent = computed(() => {
  switch (activeMenu.value) {
    case "text":
      return TextTranslation;
    case "batch":
      return BatchTranslation;
    default:
      return TextTranslation;
  }
});

const headerTitle = computed(() => {
  switch (activeMenu.value) {
    case "text":
      return "单文本翻译";
    case "batch":
      return "批量翻译";
    default:
      return "翻译引擎";
  }
});

const handleSelect = (key: string) => {
  activeMenu.value = key;
};
</script>

<style scoped>
.common-layout {
  height: 100vh;
  background-color: #f5f7fa;
}

.main-container {
  height: 100%;
}

.aside {
  background-color: #fff;
  border-right: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
  color: #303133;
  border-bottom: 1px solid #f0f2f5;
}

.el-menu-vertical {
  border-right: none;
  flex: 1;
}

.header {
  background-color: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.header-title {
  font-size: 18px;
  font-weight: 500;
  color: #303133;
}

.main-content {
  padding: 0; /* Remove padding from el-main to allow full height children */
  height: calc(100vh - 60px);
  overflow: hidden; /* Hide overflow to prevent double scrollbars */
}
</style>
