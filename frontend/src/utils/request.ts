import axios from 'axios';
import { ElMessage } from 'element-plus';

const service = axios.create({
    baseURL: '/api',
    timeout: 600000 // 10 minutes
});

service.interceptors.request.use(
    config => {
        return config;
    },
    error => {
        return Promise.reject(error);
    }
);

service.interceptors.response.use(
    response => {
        const res = response.data;
        if (res.code === 0) {
            return res;
        } else {
            ElMessage.error(res.msg || 'Error');
            return Promise.reject(new Error(res.msg || 'Error'));
        }
    },
    error => {
        console.error('err' + error);
        ElMessage.error(error.message);
        return Promise.reject(error);
    }
);

export default service;
