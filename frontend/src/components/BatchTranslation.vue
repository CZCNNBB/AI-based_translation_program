<template>
  <div class="batch-panel-container">
    <div class="batch-panel">
      <el-card class="config-card">
        <template #header>
          <div class="card-header">
            <span>批量翻译配置</span>
          </div>
        </template>

        <el-form :model="form" label-width="120px">
          <el-form-item label="输入目录" required>
            <el-input
              v-model="form.input_dir"
              placeholder="请输入待翻译文件的文件夹路径"
            />
          </el-form-item>

          <el-form-item label="输出目录" required>
            <el-input
              v-model="form.output_dir"
              placeholder="请输入翻译结果保存路径"
            />
          </el-form-item>

          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="目标语言">
                <el-select
                  v-model="form.target_lang"
                  placeholder="选择目标语言"
                  allow-create
                  filterable
                  default-first-option
                  style="width: 100%"
                >
                  <el-option label="中文" value="Chinese" />
                  <el-option label="英语" value="English" />
                  <el-option label="日语" value="Japanese" />
                  <el-option label="韩语" value="Korean" />
                  <el-option label="法语" value="French" />
                  <el-option label="德语" value="German" />
                  <el-option label="俄语" value="Russian" />
                  <el-option label="西班牙语" value="Spanish" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="领域">
                <el-input
                  v-model="form.domain"
                  placeholder="例如: 核电, 计算机, 医学"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="术语表">
                <el-input
                  v-model="form.glossary"
                  placeholder="例如: AI=人工智能, ML=机器学习"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-row :gutter="20">
            <el-col :span="12">
              <el-form-item label="文件匹配模式">
                <el-input
                  v-model="form.file_pattern"
                  placeholder="例如: *.txt, *.md"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="选项">
                <el-checkbox v-model="form.summary" label="生成摘要" />
                <el-checkbox
                  v-model="form.delete_after"
                  label="翻译后删除原文件"
                />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item>
            <el-button
              type="primary"
              @click="handleBatchTranslate"
              :loading="loading"
            >
              {{ loading ? "正在批量翻译..." : "开始批量翻译" }}
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <div v-if="result" class="result-area">
        <el-alert
          v-if="result.failed_count === 0"
          title="批量翻译完成"
          type="success"
          :description="`共处理 ${result.total_files} 个文件，全部成功！`"
          show-icon
          :closable="false"
        />
        <el-alert
          v-else
          title="批量翻译完成（包含错误）"
          type="warning"
          :description="`共处理 ${result.total_files} 个文件，成功 ${result.success_count} 个，失败 ${result.failed_count} 个。`"
          show-icon
          :closable="false"
        />

        <el-table
          :data="result.results"
          style="width: 100%; margin-top: 20px"
          border
          height="400"
        >
          <el-table-column prop="input_file" label="文件名" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="scope">
              <el-tag
                :type="scope.row.status === 'success' ? 'success' : 'danger'"
              >
                {{ scope.row.status === "success" ? "成功" : "失败" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="error" label="详情/错误信息">
            <template #default="scope">
              <span v-if="scope.row.error" class="error-text">{{
                scope.row.error
              }}</span>
              <span v-else class="success-text">翻译完成</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { batchTranslate } from "../api/translation";
import { ElMessage } from "element-plus";
import type { BatchTranslationResponse } from "../types/translation";

const loading = ref(false);
const result = ref<BatchTranslationResponse | null>(null);

const form = reactive({
  input_dir: "",
  output_dir: "",
  target_lang: "Chinese",
  domain: "",
  glossary: "",
  file_pattern: "*.txt",
  summary: false,
  delete_after: false,
});

const handleBatchTranslate = async () => {
  if (!form.input_dir || !form.output_dir) {
    ElMessage.warning("请输入输入目录和输出目录");
    return;
  }

  loading.value = true;
  result.value = null;

  try {
    const res = await batchTranslate({
      input_dir: form.input_dir,
      output_dir: form.output_dir,
      target_lang: form.target_lang,
      domain: form.domain || undefined,
      glossary: form.glossary || undefined,
      file_pattern: form.file_pattern,
      summary: form.summary,
      delete_after: form.delete_after,
    });

    if (res.data) {
      result.value = res.data;
      if (res.data.failed_count === 0) {
        ElMessage.success("批量翻译全部成功");
      } else {
        ElMessage.warning("批量翻译完成，但部分文件失败");
      }
    }
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.batch-panel-container {
  height: 100%;
  overflow-y: auto;
  padding: 20px;
  box-sizing: border-box;
}

.batch-panel {
  /* height: 100%; Remove height 100% to allow content to dictate height within scroll container */
  display: flex;
  flex-direction: column;
  gap: 20px;
  /* padding: 20px; Remove padding as container has padding */
}

.config-card {
  margin-bottom: 20px;
}

.result-area {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.error-text {
  color: #f56c6c;
}

.success-text {
  color: #67c23a;
}
</style>
