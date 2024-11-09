<template>
    <a-modal v-model:visible="isModalVisible" title="Create New Event" @ok="handleOk" @cancel="handleCancel" width="800px">
      <a-form layout="vertical">
        <!-- Event Details -->
        <a-form-item label="Event Name" required>
          <a-input v-model="event.name" />
        </a-form-item>
  
        <a-form-item label="Event Date" required>
          <a-date-picker v-model="event.date" style="width: 100%;" />
        </a-form-item>
  
        <a-form-item label="Start Time">
          <a-time-picker v-model="event.startTime" format="HH:mm" style="width: 100%;" />
        </a-form-item>
  
        <a-form-item label="End Time">
          <a-time-picker v-model="event.endTime" format="HH:mm" style="width: 100%;" />
        </a-form-item>
  
        <a-form-item label="Location" required>
          <a-input v-model="event.location" />
        </a-form-item>
  
        <a-form-item label="Description">
          <a-textarea v-model="event.description" rows="3" />
        </a-form-item>
  
        <!-- Event Image Upload -->
        <a-form-item label="Event Image">
          <a-upload :before-upload="() => false" v-model:file-list="event.image">
            <a-button icon="upload">Click to Upload</a-button>
          </a-upload>
        </a-form-item>
  
        <!-- Ticket Strategy -->
        <a-divider>Choose Your Ticket Strategy</a-divider>
        <a-radio-group v-model="event.enforceIndividualTicketLimits" @change="toggleTicketOptions">
          <a-radio value="individual">Enforce individual ticket type limits</a-radio>
          <a-radio value="total">Enforce total event capacity</a-radio>
        </a-radio-group>
  
        <!-- Ticket Options -->
        <a-divider>Ticket Types</a-divider>
        <div v-if="event.enforceIndividualTicketLimits === 'individual'">
          <div v-for="(ticket, index) in event.tickets" :key="index" class="ticket-type">
            <a-form-item label="Ticket Name" required>
              <a-input v-model="ticket.name" />
            </a-form-item>
  
            <a-form-item label="Price (£)" required>
              <a-input-number v-model="ticket.price" :min="0" step="0.01" style="width: 100%;" />
            </a-form-item>
  
            <a-form-item label="Quantity" required>
              <a-input-number v-model="ticket.quantity" :min="1" style="width: 100%;" />
            </a-form-item>
  
            <a-button type="danger" @click="removeTicket(index)" block>Remove Ticket Type</a-button>
            <a-divider />
          </div>
          <a-button type="dashed" @click="addTicketType" block>Add Ticket Type</a-button>
        </div>
  
        <!-- Total Event Capacity -->
        <a-form-item v-if="event.enforceIndividualTicketLimits === 'total'" label="Total Event Capacity" required>
          <a-input-number v-model="event.totalCapacity" :min="1" style="width: 100%;" />
        </a-form-item>
  
        <!-- Recurrence Pattern -->
        <a-divider>Event Recurrence</a-divider>
        <a-form-item label="Repeat">
          <a-select v-model="event.recurrencePattern" style="width: 100%;">
            <a-select-option value="none">None</a-select-option>
            <a-select-option value="daily">Daily</a-select-option>
            <a-select-option value="weekly">Weekly</a-select-option>
            <a-select-option value="monthly">Monthly</a-select-option>
          </a-select>
        </a-form-item>
  
        <a-form-item label="Number of Occurrences">
          <a-input-number v-model="event.occurrences" :min="1" placeholder="e.g., 5" style="width: 100%;" />
        </a-form-item>

        <!-- Custom Questions for This Event -->
        <a-divider>Custom Questions for This Event</a-divider>
        <div v-for="(question, index) in event.customQuestions" :key="index">
        <a-form-item :label="'Custom Question ' + (index + 1)">
            <a-input v-model="event.customQuestions[index]" />
        </a-form-item>
        </div>
        <a-button type="dashed" @click="addCustomQuestion" block>Add Custom Question</a-button>

  
        
      </a-form>
    </a-modal>
  </template>
  
  <script>
  import { defineComponent, ref } from 'vue';
  import { message } from 'ant-design-vue';
  
  export default defineComponent({
    name: 'EventCreationModal',
    props: {
      isModalVisible: {
        type: Boolean,
        required: true,
      },
    },
    setup(props, { emit }) {
      const event = ref({
        name: '',
        date: null,
        startTime: null,
        endTime: null,
        location: '',
        description: '',
        image: [],
        enforceIndividualTicketLimits: 'individual',
        tickets: [
          { name: '', price: 0, quantity: 0 }
        ],
        totalCapacity: 0,
        recurrencePattern: 'none',
        occurrences: 1,
        customQuestions: []
      });
  
      const addTicketType = () => {
        event.value.tickets.push({ name: '', price: 0, quantity: 0 });
      };
  
      const removeTicket = (index) => {
        event.value.tickets.splice(index, 1);
      };
  
      const toggleTicketOptions = () => {
        if (event.value.enforceIndividualTicketLimits === 'individual') {
          event.value.totalCapacity = 0;
        } else {
          event.value.tickets.forEach(ticket => (ticket.quantity = 0));
        }
      };
  
      const addCustomQuestion = () => {
        if (event.value.customQuestions.length < 10) {
          event.value.customQuestions.push('');
        } else {
          message.warning("You can add up to 10 custom questions only.");
        }
      };
  
      const handleOk = () => {
        message.success("Event created successfully!");
        emit('update:isModalVisible', false);
      };
  
      const handleCancel = () => {
        emit('update:isModalVisible', false);
      };
  
      return {
        event,
        addTicketType,
        removeTicket,
        toggleTicketOptions,
        addCustomQuestion,
        handleOk,
        handleCancel,
      };
    },
  });
  </script>
  
  <style scoped>
  .ticket-type {
    border: 1px solid #ddd;
    padding: 10px;
    border-radius: 5px;
    margin-top: 10px;
  }
  </style>
  