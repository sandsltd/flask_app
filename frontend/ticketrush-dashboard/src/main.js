// src/main.js
import { createApp } from 'vue';
import App from './App.vue';
import Antd from 'ant-design-vue';

// Remove the import of 'ant-design-vue/dist/ant-design-vue.css' if we have moved it to public

const app = createApp(App);
app.use(Antd);
app.mount('#app');
