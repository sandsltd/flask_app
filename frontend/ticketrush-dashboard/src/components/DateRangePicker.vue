<template>
    <a-range-picker @change="onDateChange" style="margin-bottom: 16px;" />
  </template>
  
  <script>
  import { defineComponent } from 'vue';
  
  export default defineComponent({
    name: 'DateRangePicker',
    methods: {
      onDateChange(dates) {
        // Add functionality to filter data based on selected date range
        console.log("Selected dates:", dates);
      },
    },
  });
  </script>
  