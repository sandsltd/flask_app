<template>
  <a-layout style="min-height: 100vh">
    <!-- Sidebar with quick actions -->
    <a-layout-sider collapsible v-model:collapsed="collapsed" theme="light" :style="{ backgroundColor: '#FF3131' }">
      <div class="logo">
        <img src="https://ticketrush.io/wp-content/uploads/2024/10/logo_T-1.png" alt="Ticketrush Logo" class="brand-logo" />
      </div>
      <a-menu theme="light" mode="inline" :default-selected-keys="['1']" :style="{ backgroundColor: '#FF3131', color: 'white' }">
        <a-menu-item key="1" icon="dashboard" style="color: white;"> Dashboard </a-menu-item>
        <a-menu-item key="2" icon="calendar" style="color: white;"> Calendar </a-menu-item>
        <a-menu-item key="3" icon="bar-chart" style="color: white;"> Analytics </a-menu-item>
        <a-menu-item key="4" icon="setting" style="color: white;"> Settings </a-menu-item>
      </a-menu>
    </a-layout-sider>

    <!-- Main Layout -->
    <a-layout>
      <!-- Top Header -->
      <a-layout-header :style="{ backgroundColor: 'white', padding: '0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }">
        <h2 :style="{ marginLeft: '16px', color: '#FF3131' }">Welcome back to your dashboard!</h2>
        <div style="display: flex; align-items: center;">
          <ProfileDropdown @logout="handleLogout" />
          <a-button type="primary" :style="{ backgroundColor: '#FF3131', borderColor: '#FF3131', color: 'white', marginLeft: '16px' }" @click="showModal">
            <PlusOutlined /> Create New Event
          </a-button>
        </div>
      </a-layout-header>

      <!-- Main Content Area -->
      <a-layout-content style="margin: 24px 16px; padding: 24px; background: #f0f2f5;">
        <DateRangePicker />
        
        <!-- Statistics Row -->
        <a-row gutter="16" class="stats-row">
          <a-col :span="6">
            <a-card title="Total Sales" bordered>
              <h2>{{ totalSales }}</h2>
              <p>Tickets Sold</p>
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card title="Upcoming Events" bordered>
              <h2>{{ upcomingEvents }}</h2>
              <p>Events</p>
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card title="Total Revenue" bordered>
              <h2>£{{ revenue }}</h2>
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card title="Total Users" bordered>
              <h2>{{ totalUsers }}</h2>
              <p>Users</p>
            </a-card>
          </a-col>
        </a-row>

        <!-- Charts Section -->
        <a-row gutter="16" style="margin-top: 24px;">
          <a-col :span="12">
            <a-card title="Monthly Sales">
              <LineChart :data="lineChartData" :options="lineChartOptions" />
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="Revenue Breakdown">
              <BarChart :data="barChartData" :options="barChartOptions" />
            </a-card>
          </a-col>
        </a-row>

        <!-- Recent Activities Table -->
        <a-row style="margin-top: 24px;">
          <a-col :span="24">
            <a-card title="Recent Activities">
              <a-table :columns="activityColumns" :dataSource="activities" rowKey="id" style="margin-top: 16px;" />
            </a-card>
          </a-col>
        </a-row>

        <!-- Calendar Section -->
        <a-row style="margin-top: 24px;">
          <a-col :span="24">
            <a-card title="Event Calendar">
              <a-calendar v-model="calendarDate" />
            </a-card>
          </a-col>
        </a-row>

        <!-- Notification and Event Creation Modal -->
        <Notification ref="notification" />
        <EventCreationModal :isModalVisible="isModalVisible" @update:isModalVisible="isModalVisible = $event" />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script>
import { defineComponent, ref } from 'vue';
import { message } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import LineChart from './LineChart.vue';
import BarChart from './BarChart.vue';
import Notification from './Notification.vue';
import ProfileDropdown from './ProfileDropdown.vue';
import DateRangePicker from './DateRangePicker.vue';
import EventCreationModal from './EventCreationModal.vue';
import QuickActions from './QuickActions.vue';

export default defineComponent({
  name: 'Dashboard',
  components: {
    LineChart,
    BarChart,
    Notification,
    ProfileDropdown,
    DateRangePicker,
    EventCreationModal,
    QuickActions,
    PlusOutlined,
  },
  setup() {
    const collapsed = ref(false);
    const calendarDate = ref(new Date());
    const totalSales = ref(1500);
    const upcomingEvents = ref(5);
    const revenue = ref(10000);
    const totalUsers = ref(120);

    const isModalVisible = ref(false);

    const lineChartData = {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
      datasets: [{ label: 'Tickets Sold', backgroundColor: 'rgba(75,192,192,0.2)', borderColor: 'rgba(75,192,192,1)', data: [65, 59, 80, 81, 56, 55] }],
    };
    const lineChartOptions = { responsive: true, maintainAspectRatio: false };

    const barChartData = {
      labels: ['Products', 'Services', 'Subscriptions'],
      datasets: [{ label: 'Revenue (£)', backgroundColor: ['#3b82f6', '#10b981', '#fbbf24'], data: [1200, 900, 500] }],
    };
    const barChartOptions = { responsive: true, maintainAspectRatio: false };

    const activities = [{ id: 1, activity: 'User John purchased 10 tickets', date: '2024-12-01' }, { id: 2, activity: 'Added new event "Music Festival"', date: '2024-11-25' }, { id: 3, activity: 'Processed 50 ticket refunds', date: '2024-11-20' }];
    const activityColumns = [{ title: 'Activity', dataIndex: 'activity', key: 'activity' }, { title: 'Date', dataIndex: 'date', key: 'date' }];

    const showModal = () => {
      message.success('New event modal opened!');
      isModalVisible.value = true;
      // Show notification
      const notificationRef = ref(null);
      notificationRef.value.showNotification();
    };

    const handleLogout = () => {
      console.log('User logged out');
      // Redirect to login or clear user session
    };

    return {
      collapsed,
      calendarDate,
      totalSales,
      upcomingEvents,
      revenue,
      totalUsers,
      lineChartData,
      lineChartOptions,
      barChartData,
      barChartOptions,
      activities,
      activityColumns,
      showModal,
      isModalVisible,
      handleLogout,
    };
  },
});
</script>

<style scoped>
.logo {
  height: 64px;
  margin: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.brand-logo {
  max-width: 100%;
  height: auto;
}

.dashboard h2 {
  margin: 0;
  color: #FF3131;
}

a-layout-content {
  background: #f0f2f5;
  padding: 24px;
}

.stats-row .ant-card {
  text-align: center;
}

.stats-row h2 {
  font-size: 2em;
  color: #FF3131;
}
</style>
