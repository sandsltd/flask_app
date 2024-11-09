<template>
    <a-layout-sider collapsible theme="light" width="200">
      <a-menu mode="vertical">
        <a-menu-item key="1" icon="plus" @click="showEventModal">Create Event</a-menu-item>
        <a-menu-item key="2" icon="file">Generate Report</a-menu-item>
        <a-menu-item key="3" icon="upload">Import Data</a-menu-item>
      </a-menu>
    </a-layout-sider>
  </template>
  
  <script>
  import { defineComponent } from 'vue';
  
  export default defineComponent({
    name: 'QuickActions',
    methods: {
      showEventModal() {
        this.$emit('showModal');
      },
    },
  });
  </script>
  