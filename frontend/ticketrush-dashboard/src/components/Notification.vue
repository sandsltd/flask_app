<template>
    <div>
      <!-- Optional button or trigger if needed, or it can be triggered by a method -->
      <a-button type="primary" @click="showNotification">Show Notification</a-button>
    </div>
  </template>
  
  <script>
  import { notification } from 'ant-design-vue';
  
  export default {
    name: 'NotificationComponent',
    methods: {
      showNotification() {
        notification.success({
          message: 'Event Created',
          description: 'A new event has been successfully created.',
          duration: 3,
        });
      },
    },
  };
  </script>
  
  <style scoped>
  /* Add any styles specific to this component here */
  </style>
  