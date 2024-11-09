<template>
  <div>
    <canvas ref="canvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { Chart, LineController, LineElement, PointElement, LinearScale, Title, CategoryScale } from 'chart.js';

Chart.register(LineController, LineElement, PointElement, LinearScale, Title, CategoryScale);

export default {
  props: ['data', 'options'],
  setup(props) {
    const canvas = ref(null);

    onMounted(() => {
      new Chart(canvas.value, {
        type: 'line',
        data: props.data,
        options: props.options,
      });
    });

    return { canvas };
  },
};
</script>
