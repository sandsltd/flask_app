import React, { useState, useEffect } from 'react';
import { Search, Calendar, Clock, MapPin, Users, PoundSterling, ChevronDown, ChevronUp } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

const EventDashboard = () => {
  const [events, setEvents] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [sortBy, setSortBy] = useState('date');
  const [sortOrder, setSortOrder] = useState('asc');
  const [expandedEvents, setExpandedEvents] = useState(new Set());

  // Fetch events from Flask API on component mount
  useEffect(() => {
    fetch('https://bookings.ticketrush.io/api/events')
      .then(response => response.json())
      .then(data => setEvents(data))
      .catch(error => console.error('Error fetching events:', error));
  }, []);

  // Filter and sort functions (existing code remains the same)
  const filteredEvents = events
    .filter(event => {
      const matchesSearch = event.name.toLowerCase().includes(searchTerm.toLowerCase()) || event.location.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesFilter = filterStatus === 'all' || event.status === filterStatus;
      return matchesSearch && matchesFilter;
    })
    .sort((a, b) => {
      const sortValue = event => {
        switch (sortBy) {
          case 'date':
            return new Date(event.date);
          case 'name':
            return event.name;
          case 'revenue':
            return event.total_revenue;
          default:
            return new Date(event.date);
        }
      };
      const aValue = sortValue(a);
      const bValue = sortValue(b);
      return sortOrder === 'asc' ? (aValue > bValue ? 1 : -1) : (aValue < bValue ? 1 : -1);
    });

  const toggleEventExpand = eventId => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Search and Filter Controls */}
      <div className="mb-6 space-y-4">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search events..."
              className="pl-10 p-2 w-full border rounded-lg"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <select
            className="p-2 border rounded-lg"
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="all">All Events</option>
            <option value="upcoming">Upcoming</option>
            <option value="past">Past</option>
          </select>
          <select
            className="p-2 border rounded-lg"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="date">Sort by Date</option>
            <option value="name">Sort by Name</option>
            <option value="revenue">Sort by Revenue</option>
          </select>
          <button
            className="p-2 border rounded-lg"
            onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
          >
            {sortOrder === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>
  
      {/* Events Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredEvents.map(event => (
          <Card key={event.id} className="overflow-hidden">
            <CardHeader className="bg-red-50">
              <CardTitle className="text-xl font-bold text-red-600">{event.name}</CardTitle>
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-gray-500" />
                  <span>{new Date(event.date).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-gray-500" />
                  <span>{event.location}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-gray-500" />
                  <span>{event.tickets_sold} / {event.ticket_quantity} tickets sold</span>
                </div>
                <div className="flex items-center gap-2">
                  <PoundSterling className="h-4 w-4 text-gray-500" />
                  <span>£{event.total_revenue.toFixed(2)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-gray-500" />
                  <span className="capitalize">{event.status}</span>
                </div>
              </div>
  
              {/* Expandable Ticket Breakdown */}
              <div>
                <button
                  onClick={() => toggleEventExpand(event.id)}
                  className="w-full text-left flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100"
                >
                  <span>Ticket Breakdown</span>
                  {expandedEvents.has(event.id) ? 
                    <ChevronUp className="h-4 w-4" /> : 
                    <ChevronDown className="h-4 w-4" />
                  }
                </button>
                
                {expandedEvents.has(event.id) && (
                  <div className="mt-2 space-y-2">
                    {event.ticket_breakdown.map((ticket, idx) => (
                      <div key={idx} className="p-2 bg-gray-50 rounded-lg">
                        <div className="font-medium">{ticket.name}</div>
                        <div className="text-sm text-gray-600">
                          £{ticket.price.toFixed(2)} - {ticket.tickets_sold}/{ticket.total_quantity} sold
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
  
              {/* Action Buttons */}
              <div className="flex gap-2 pt-4">
                <a href={`/view_attendees/${event.id}`} className="flex-1 px-4 py-2 bg-blue-500 text-white rounded-lg text-center hover:bg-blue-600">
                  Attendees
                </a>
                <a href={`/edit_event/${event.id}`} className="flex-1 px-4 py-2 bg-red-500 text-white rounded-lg text-center hover:bg-red-600">
                  Edit
                </a>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default EventDashboard;
