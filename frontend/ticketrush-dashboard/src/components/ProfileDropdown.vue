<template>
    <a-dropdown trigger="click">
      <div style="display: flex; align-items: center; cursor: pointer;" @click="showDropdown">
        <a-avatar style="margin-right: 8px;" icon="user" />
        <span>{{ username }}</span>
        <a-icon type="down" style="margin-left: 8px;" />
      </div>
      <template #overlay>
        <a-menu @click="onMenuClick">
          <a-menu-item key="profile">
            <a-icon type="user" /> Profile
          </a-menu-item>
          <a-menu-item key="settings">
            <a-icon type="setting" /> Settings
          </a-menu-item>
          <a-menu-item key="logout">
            <a-icon type="logout" /> Logout
          </a-menu-item>
        </a-menu>
      </template>
    </a-dropdown>
  </template>
  
  <script>
  import { defineComponent, ref } from 'vue';
  import { UserOutlined, SettingOutlined, LogoutOutlined, DownOutlined } from '@ant-design/icons-vue';
  
  export default defineComponent({
    name: 'ProfileDropdown',
    components: {
      UserOutlined,
      SettingOutlined,
      LogoutOutlined,
      DownOutlined,
    },
    setup(_, { emit }) {
      const username = ref('John Doe'); // Placeholder username
  
      const onMenuClick = ({ key }) => {
        if (key === 'profile') {
          console.log('Navigating to profile...');
        } else if (key === 'settings') {
          console.log('Navigating to settings...');
        } else if (key === 'logout') {
          console.log('Logging out...');
          emit('logout');
        }
      };
  
      return {
        username,
        onMenuClick,
      };
    },
  });
  </script>
  
  <style scoped>
  /* Add any custom styling here if needed */
  </style>
  