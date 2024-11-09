<template>
  <div>
    <Bar :data="chartData" :options="chartOptions" />
  </div>
</template>

<script>
import { Bar } from 'vue-chartjs';
import { Chart, registerables } from 'chart.js';

Chart.register(...registerables);

export default {
  name: 'BarChart',
  components: {
    Bar
  },
  props: {
    data: {
      type: Object,
      required: true
    },
    options: {
      type: Object,
      default: () => ({
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              stepSize: 50
            }
          }
        }
      })
    }
  },
  computed: {
    chartData() {
      return this.data;
    },
    chartOptions() {
      return this.options;
    }
  }
};
</script>

<style scoped>
div {
  height: 300px;
}
</style>
