<template>
  <div class="translation-panel">
    <div class="controls">
      <el-form :inline="true" :model="form" class="demo-form-inline">
        <el-form-item label="目标语言">
          <el-select
            v-model="form.target_lang"
            placeholder="选择目标语言"
            style="width: 150px"
            allow-create
            filterable
            default-first-option
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

        <el-form-item label="领域">
          <el-input
            v-model="form.domain"
            placeholder="例如: 核电, 计算机, 医学"
            style="width: 200px"
          />
        </el-form-item>

        <el-form-item label="术语表">
          <el-input
            v-model="form.glossary"
            placeholder="例如: AI=人工智能, ML=机器学习"
            style="width: 150px"
          />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="form.summary" label="生成摘要" border />
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="handleTranslate"
            :loading="loading"
            :icon="loading ? Loading : VideoPlay"
          >
            {{ loading ? "翻译中..." : "开始翻译" }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <div class="content-area">
      <el-row :gutter="20" style="height: 100%">
        <el-col :span="12" style="height: 100%">
          <el-card class="box-card input-card" shadow="hover">
            <template #header>
              <div class="card-header">
                <span>原文</span>
                <el-button
                  text
                  bg
                  size="small"
                  @click="form.text = ''"
                  v-if="form.text"
                  >清空</el-button
                >
              </div>
            </template>
            <el-input
              v-model="form.text"
              type="textarea"
              placeholder="请输入要翻译的文本..."
              resize="none"
              class="translation-textarea"
            />
          </el-card>
        </el-col>

        <el-col :span="12" style="height: 100%">
          <el-card
            class="box-card output-card"
            shadow="hover"
            v-loading="loading"
            element-loading-text="正在思考翻译中..."
          >
            <template #header>
              <div class="card-header">
                <span>译文</span>
                <el-button
                  text
                  bg
                  size="small"
                  @click="copyResult"
                  v-if="resultText"
                  >复制</el-button
                >
              </div>
            </template>
            <el-input
              v-model="resultText"
              type="textarea"
              readonly
              placeholder="翻译结果将显示在这里..."
              resize="none"
              class="translation-textarea"
            />

            <div v-if="summaryText" class="summary-box">
              <el-divider content-position="left">摘要</el-divider>
              <p>{{ summaryText }}</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { translateText } from "../api/translation";
import { ElMessage } from "element-plus";
import { VideoPlay, Loading } from "@element-plus/icons-vue";

const loading = ref(false);
const resultText = ref("");
const summaryText = ref("");

const form = reactive({
  text: "",
  target_lang: "Chinese",
  domain: "",
  glossary: "",
  summary: false,
});

const handleTranslate = async () => {
  if (!form.text.trim()) {
    ElMessage.warning("请输入要翻译的文本");
    return;
  }

  loading.value = true;
  resultText.value = "";
  summaryText.value = "";

  try {
    const res = await translateText({
      text: form.text,
      target_lang: form.target_lang,
      domain: form.domain || undefined,
      glossary: form.glossary || undefined,
      summary: form.summary,
    });

    if (res.data) {
      resultText.value = res.data.translated_text;
      if (res.data.summary) {
        summaryText.value = res.data.summary;
      }
      ElMessage.success("翻译完成");
    }
  } catch (error) {
    console.error(error);
    // Error is handled in request interceptor
  } finally {
    loading.value = false;
  }
};

const copyResult = async () => {
  if (resultText.value) {
    try {
      await navigator.clipboard.writeText(resultText.value);
      ElMessage.success("复制成功");
    } catch (err) {
      ElMessage.error("复制失败");
    }
  }
};
</script>

<style scoped>
.translation-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px; /* Add padding here */
  box-sizing: border-box;
}

.controls {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  flex-shrink: 0;
}

.content-area {
  flex: 1;
  min-height: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.input-card,
.output-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

:deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 10px;
  height: calc(100% - 60px);
}

.translation-textarea {
  height: 100%;
}

:deep(.el-textarea__inner) {
  height: 100% !important;
  border: none;
  box-shadow: none;
  font-size: 16px;
  line-height: 1.6;
  padding: 10px;
  background-color: #f9fafc;
}

:deep(.el-textarea__inner:focus) {
  box-shadow: none;
  background-color: #fff;
}

.summary-box {
  margin-top: 10px;
  padding: 10px;
  background-color: #ecf5ff;
  border-radius: 4px;
  font-size: 14px;
  color: #606266;
  max-height: 150px;
  overflow-y: auto;
  flex-shrink: 0;
}
</style>
