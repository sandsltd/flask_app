<template>
    <div class="centered-container">
      <div class="dashboard-container">
        <!-- Business Logo and Welcome Message -->
        <div class="business-header">
          <img v-if="user.business_logo_url" :src="user.business_logo_url" :alt="user.business_name + ' Logo'" class="business-logo" />
          <div v-else class="business-logo-placeholder">{{ user.business_name.slice(0, 2).toUpperCase() }}</div>
          <h1>Welcome back to {{ user.business_name }}'s Dashboard!</h1>
        </div>
  
        <!-- Flash Messages -->
        <div v-if="flashMessages.length" class="flash-messages">
          <div v-for="(message, index) in flashMessages" :key="index" :class="['alert', 'alert-' + message.type]">
            {{ message.text }}
          </div>
        </div>
  
        <!-- Summary Section -->
        <div class="summary-section">
          <h2>Since you've been using TicketRush</h2>
          <p><strong>Tickets Sold:</strong> {{ totalTicketsSold }}</p>
          <p><strong>Total Revenue Generated:</strong> £{{ totalRevenue.toFixed(2) }}</p>
          <p>Thanks for choosing TicketRush for your event ticketing needs!</p>
        </div>
  
        <!-- Stripe Account Access Section -->
        <div class="summary-section">
          <h3>Manage Your Payments</h3>
          <p>
            To view detailed payment history or manage your account, visit your
            <a href="https://dashboard.stripe.com/login" target="_blank" class="stripe-link">Stripe Dashboard</a>.
          </p>
        </div>
  
        <!-- Action Buttons -->
        <div class="action-buttons">
          <router-link to="/create_event" class="button">Create New Event</router-link>
          <router-link to="/manage-default-questions" class="button">Account Settings</router-link>
        </div>
  
        <!-- Filter Form -->
        <div class="filter-form">
          <label for="filter">Filter:</label>
          <select v-model="filter" @change="fetchDashboardData">
            <option value="all">All Events</option>
            <option value="upcoming">Upcoming Events</option>
            <option value="past">Past Events</option>
          </select>
        </div>
  
        <!-- Events Section -->
        <h2>Your Events</h2>
        <ul>
          <li v-for="event in events" :key="event.id" class="event-item">
            <strong>{{ event.name }}</strong> - {{ formatDate(event.date) }}
            <br />
            <strong>Location:</strong> {{ event.location }}
            <br />
            <strong>Tickets Sold:</strong> {{ event.tickets_sold }} / {{ event.ticket_quantity }}
            <button @click="toggleBreakdown(event.id)" class="breakdown-button">View Breakdown</button>
  
            <!-- Ticket Breakdown -->
            <div v-if="showBreakdown[event.id]" class="ticket-breakdown">
              <table>
                <tr>
                  <th>Ticket Type</th>
                  <th>Price</th>
                  <th>Sold</th>
                  <th v-if="event.enforce_individual_ticket_limits">Remaining</th>
                  <th>Total Quantity</th>
                </tr>
                <tr v-for="ticket in event.ticket_breakdown" :key="ticket.name">
                  <td>{{ ticket.name }}</td>
                  <td>£{{ ticket.price.toFixed(2) }}</td>
                  <td>{{ ticket.tickets_sold }}</td>
                  <td v-if="event.enforce_individual_ticket_limits">{{ ticket.tickets_remaining }}</td>
                  <td>{{ ticket.total_quantity }}</td>
                </tr>
              </table>
            </div>
  
            <!-- Event Details and Links -->
            <br />
            <strong>Tickets Remaining:</strong> {{ event.tickets_remaining }}
            <br />
            <strong>Total Revenue:</strong> £{{ event.total_revenue.toFixed(2) }}
            <br />
            <strong>Status:</strong> {{ event.status }}
            <br />
            <router-link :to="{ name: 'viewAttendees', params: { eventId: event.id } }">View Attendees</router-link> |
            <router-link :to="{ name: 'editEvent', params: { eventId: event.id } }">Edit</router-link> |
            <router-link :to="{ name: 'createWebpage', params: { eventId: event.id } }">Create A Webpage For This Event</router-link>
            <button @click="deleteEvent(event.id)" class="button delete-button">Delete</button>
          </li>
          <li v-if="events.length === 0">No events yet.</li>
        </ul>
  
        <!-- Embed Code Section -->
        <div class="embed-section">
          <h3>Your Embed Code</h3>
          <pre>{{ embedCode }}</pre>
          <button @click="copyEmbedCode" class="copy-button">Copy to Clipboard</button>
          <p>Copy this code and paste it into your website to display your events.</p>
        </div>
  
        <!-- Logout Link -->
        <div class="links">
          <router-link to="/logout" class="button">Logout</router-link>
        </div>
      </div>
    </div>
  </template>
  
  <script>
  
  import axios from 'axios';
  
  export default {
    data() {
      return {
        user: {},
        events: [],
        flashMessages: [],
        totalTicketsSold: 0,
        totalRevenue: 0,
        filter: 'upcoming',
        showBreakdown: {},
      };
    },
    computed: {
      embedCode() {
        return `<script src="https://bookings.ticketrush.io/embed/${this.user.unique_id}"></script>`;
      },
    },
    methods: {
      async fetchDashboardData() {
        try {
          const response = await axios.get(`/api/dashboard?filter=${this.filter}`);
          const { user, events, total_tickets_sold, total_revenue, flash_messages } = response.data;
          this.user = user;
          this.events = events;
          this.totalTicketsSold = total_tickets_sold;
          this.totalRevenue = total_revenue;
          this.flashMessages = flash_messages || [];
        } catch (error) {
          console.error('Error fetching dashboard data:', error);
        }
      },
      formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleDateString();
      },
      toggleBreakdown(eventId) {
        this.$set(this.showBreakdown, eventId, !this.showBreakdown[eventId]);
      },
      copyEmbedCode() {
        navigator.clipboard.writeText(this.embedCode)
          .then(() => alert('Embed code copied to clipboard!'))
          .catch(err => console.error('Failed to copy embed code:', err));
      },
      async deleteEvent(eventId) {
        if (confirm('Are you sure you want to delete this event? This action cannot be undone.')) {
          try {
            await axios.post(`/api/delete_event/${eventId}`);
            this.fetchDashboardData();
          } catch (error) {
            console.error('Error deleting event:', error);
          }
        }
      },
    },
    mounted() {
      this.fetchDashboardData();
    },
  };
  </script>
  
  <style scoped>
  /* Add scoped styles for the component */
  </style>
  