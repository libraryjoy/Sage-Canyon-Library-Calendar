#!/usr/bin/env python3
"""
School Library Calendar Runner
This script runs the interactive school library calendar without needing Jupyter notebook.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import json
import os
import re

# For Google Sheets integration (you'll need to set up authentication)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

print("All packages imported successfully!")

# Sample data structure (replace with your actual Google Sheets integration)
# This represents the data from your Google Sheet
sample_schedule_data = {
    '2025-08-14': {'day_type': 'A Day', 'notes': 'First Day of School'},
    '2025-08-15': {'day_type': 'B Day', 'notes': ''},
    '2025-08-18': {'day_type': 'A Day', 'notes': ''},
    '2025-08-19': {'day_type': 'B Day', 'notes': ''},
    '2025-08-20': {'day_type': 'A Day', 'notes': 'Early Out'},
    '2025-08-21': {'day_type': 'B Day', 'notes': ''},
    '2025-08-22': {'day_type': 'A Day', 'notes': ''},
    '2025-08-25': {'day_type': 'B Day', 'notes': ''},
    '2025-08-26': {'day_type': 'A Day', 'notes': ''},
    '2025-08-27': {'day_type': 'B Day', 'notes': ''},
    '2025-08-28': {'day_type': 'A Day', 'notes': ''},
    '2025-08-29': {'day_type': 'B Day', 'notes': ''},
    '2025-09-02': {'day_type': 'B Day', 'notes': ''},
    '2025-09-03': {'day_type': 'A Day', 'notes': ''},
    '2025-09-04': {'day_type': 'B Day', 'notes': ''},
    '2025-09-05': {'day_type': 'A Day', 'notes': ''},
    '2025-09-08': {'day_type': 'B Day', 'notes': ''}
}

# Time periods based on your schedule
time_periods = {
    'A1/B5': {'start': '08:15', 'end': '09:35', 'regular': True},
    'Den Time': {'start': '09:30', 'end': '10:15', 'regular': True},
    'A2/B6': {'start': '10:20', 'end': '11:35', 'regular': True},
    'A3/B7': {'start': '12:10', 'end': '13:25', 'regular': True},
    'A4/B8': {'start': '13:30', 'end': '14:45', 'regular': True},
    'After School': {'start': '14:45', 'end': '15:30', 'regular': True}
}

# Wednesday early out times
wednesday_times = {
    'A1/B5': {'start': '08:15', 'end': '09:25', 'regular': False},
    'Den Time': {'start': 'Not Available', 'end': '', 'regular': False},
    'A2/B6': {'start': '09:30', 'end': '10:40', 'regular': False},
    'A3/B7': {'start': '10:50', 'end': '12:00', 'regular': False},
    'A4/B8': {'start': '12:05', 'end': '13:15', 'regular': False},
    'After School': {'start': '13:15', 'end': '13:45', 'regular': False}
}

print("Sample data loaded successfully!")

# Function to get schedule data for a specific week
def get_week_schedule(start_date_str):
    """Get schedule data for a specific week starting from Monday"""
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    week_schedule = {}
    
    for i in range(5):  # Monday to Friday
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        
        if date_str in sample_schedule_data:
            week_schedule[current_date.strftime('%A')] = {
                'date': current_date.strftime('%m/%d'),
                'day_type': sample_schedule_data[date_str]['day_type'],
                'notes': sample_schedule_data[date_str]['notes'],
                'is_wednesday': current_date.weekday() == 2  # Wednesday is 2
            }
        else:
            week_schedule[current_date.strftime('%A')] = {
                'date': current_date.strftime('%m/%d'),
                'day_type': 'No School',
                'notes': '',
                'is_wednesday': current_date.weekday() == 2
            }
    
    return week_schedule

# Test the function
week_data = get_week_schedule('2025-08-18')
print("Week schedule for August 18-22, 2025:")
for day, data in week_data.items():
    print(f"{day}: {data['date']} - {data['day_type']} - {data['notes']}")

# Create the interactive calendar using Dash
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Store bookings (in a real app, this would be a database)
bookings = {}

# Create the calendar layout
def create_calendar_layout(week_data):
    """Create the calendar grid layout"""
    
    # Header row with days
    header_row = html.Tr([
        html.Th("Time Period", style={'width': '150px', 'textAlign': 'center', 'backgroundColor': '#f8f9fa'})
    ])
    
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        if day in week_data:
            data = week_data[day]
            header_cell = html.Th([
                html.Div(f"{day.upper()} {data['date']}", style={'fontWeight': 'bold'}),
                html.Div(data['day_type'], style={'fontSize': '12px', 'color': '#666'}),
                html.Div(data['notes'], style={'fontSize': '10px', 'color': '#ff4444' if 'Early Out' in data['notes'] else '#666'})
            ], style={'width': '200px', 'textAlign': 'center', 'backgroundColor': '#f8f9fa', 'padding': '10px'})
        else:
            header_cell = html.Th(day.upper(), style={'width': '200px', 'textAlign': 'center', 'backgroundColor': '#f8f9fa'})
        header_row.children.append(header_cell)
    
    # Create time period rows
    rows = [header_row]
    
    for period, times in time_periods.items():
        row_cells = [
            html.Td(period, style={'width': '150px', 'textAlign': 'center', 'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'})
        ]
        
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
            if day in week_data:
                data = week_data[day]
                is_wednesday = data['is_wednesday']
                
                # Use Wednesday times if it's Wednesday and it's an early out day
                if is_wednesday and 'Early Out' in data['notes']:
                    period_times = wednesday_times[period]
                else:
                    period_times = times
                
                # Create booking slots
                if period_times['start'] != 'Not Available':
                    # Calculate time splits for First Half, Second Half, Entire Period
                    start_time = period_times['start']
                    end_time = period_times['end']
                    
                    # Simple time split (you can make this more sophisticated)
                    if ':' in start_time and ':' in end_time:
                        start_minutes = int(start_time.split(':')[0]) * 60 + int(start_time.split(':')[1])
                        end_minutes = int(end_time.split(':')[0]) * 60 + int(end_time.split(':')[1])
                        mid_minutes = start_minutes + (end_minutes - start_minutes) // 2
                        
                        mid_time = f"{mid_minutes // 60:02d}:{mid_minutes % 60:02d}"
                        
                        booking_slots = [
                            html.Button(f"FIRST HALF ({start_time} - {mid_time})", 
                                      id="test-booking-button",
                                      style={'cursor': 'pointer', 'padding': '4px', 'margin': '2px', 'border': '2px solid #007bff', 'backgroundColor': '#f8f9fa', 'borderRadius': '4px', 'fontWeight': 'bold', 'width': '100%', 'fontSize': '10px'})
                        ]
                    else:
                        booking_slots = [
                            html.Div(f"ENTIRE PERIOD ({start_time} - {end_time})", 
                                    id=f"booking-{day}-{period}-entire",
                                    className="booking-slot",
                                    style={'cursor': 'pointer', 'padding': '2px', 'margin': '1px', 'border': '1px solid #ddd', 'backgroundColor': '#fff'})
                        ]
                else:
                    booking_slots = [
                        html.Div("Not Available", 
                                style={'padding': '2px', 'margin': '1px', 'border': '1px solid #ddd', 'backgroundColor': '#f8f9fa', 'color': '#ff4444'})
                    ]
                
                cell_content = html.Div(booking_slots, style={'fontSize': '10px'})
                row_cells.append(html.Td(cell_content, style={'width': '200px', 'textAlign': 'center', 'border': '1px solid #ddd'}))
            else:
                row_cells.append(html.Td("No School", style={'width': '200px', 'textAlign': 'center', 'border': '1px solid #ddd', 'backgroundColor': '#f8f9fa'}))
        
        rows.append(html.Tr(row_cells))
    
    return html.Table(rows, style={'width': '100%', 'borderCollapse': 'collapse', 'fontSize': '12px'})

# Create the main app layout
app.layout = dbc.Container([
    html.H1("School Library Calendar", className="text-center mb-4"),
    
    # Week selector
    dbc.Row([
        dbc.Col([
            html.Label("Select Week:"),
            dcc.DatePickerSingle(
                id='week-selector',
                date='2025-08-18',
                display_format='MM/DD/YYYY'
            )
        ], width=3),
        dbc.Col([
            html.Button("Previous Week", id="prev-week", className="btn btn-secondary"),
            html.Button("Next Week", id="next-week", className="btn btn-secondary", style={'marginLeft': '10px'})
        ], width=6)
    ], className="mb-3"),
    
    # Calendar display
    html.Div(id='calendar-container'),
    
    # Test button
    html.Button("TEST BOOKING BUTTON", id="test-booking-button", 
                style={'margin': '20px', 'padding': '10px', 'backgroundColor': 'red', 'color': 'white', 'fontSize': '16px'}),
    
    # Display area for button clicks
    html.Div(id="click-display", style={'margin': '20px', 'padding': '10px', 'backgroundColor': 'yellow', 'border': '2px solid black'}),
    
    # Simple test output
    html.Div(id="test-output", style={'margin': '20px', 'padding': '10px', 'backgroundColor': 'lightblue', 'border': '2px solid black'}),
    
    # Booking modal
    dbc.Modal([
        dbc.ModalHeader("Book Library Time"),
        dbc.ModalBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Teacher Name:"),
                    dbc.Input(id="teacher-name", type="text", placeholder="Enter teacher name")
                ])
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Class/Subject:"),
                    dbc.Input(id="class-subject", type="text", placeholder="Enter class or subject")
                ])
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Notes (optional):"),
                    dbc.Textarea(id="booking-notes", placeholder="Enter any additional notes")
                ])
            ], className="mb-3")
        ]),
        dbc.ModalFooter([
            dbc.Button("Cancel", id="cancel-booking", className="ml-auto"),
            dbc.Button("Book", id="confirm-booking", color="primary")
        ])
    ], id="booking-modal", size="lg"),
    
    # Hidden div to store booking data
    html.Div(id="booking-data", style={'display': 'none'})
    
], fluid=True)

print("Calendar layout created successfully!")

# Callbacks for the interactive calendar
@app.callback(
    Output('calendar-container', 'children'),
    Input('week-selector', 'date')
)
def update_calendar(selected_date):
    """Update the calendar when a new week is selected"""
    if selected_date:
        week_data = get_week_schedule(selected_date)
        return create_calendar_layout(week_data)
    return "No date selected"



# Add click handlers for booking slots using a simpler approach
@app.callback(
    Output('booking-modal', 'is_open'),
    Output('booking-data', 'children'),
    [Input('confirm-booking', 'n_clicks'),
     Input('cancel-booking', 'n_clicks')],
    [State('booking-modal', 'is_open')]
)
def handle_modal_buttons(confirm_clicks, cancel_clicks, is_open):
    """Handle modal open/close buttons"""
    if confirm_clicks or cancel_clicks:
        return not is_open, ""
    return is_open, ""

# Add callback for booking slot button clicks using a simpler approach
@app.callback(
    Output('booking-modal', 'is_open', allow_duplicate=True),
    Output('booking-data', 'children', allow_duplicate=True),
    [Input('test-booking-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_booking_button_click(n_clicks):
    """Handle clicks on booking buttons"""
    if n_clicks:
        print(f"Booking button clicked! n_clicks: {n_clicks}")  # Debug print
        
        booking_info = {
            'slot_type': 'test',
            'start_time': '08:15',
            'end_time': '09:35',
            'button_text': 'Test Booking'
        }
        
        return True, json.dumps(booking_info)  # Open modal with booking info
    
    return False, ""

# Add a simple callback to show when any button is clicked
@app.callback(
    Output('click-display', 'children'),
    [Input('test-booking-button', 'n_clicks')],
    prevent_initial_call=True
)
def simple_button_click(n_clicks):
    """Simple button click handler"""
    if n_clicks:
        print(f"Button clicked! Count: {n_clicks}")
        return f"Button was clicked {n_clicks} times!"
    return "No clicks yet"

# Add a very simple test callback
@app.callback(
    Output('test-output', 'children'),
    [Input('test-booking-button', 'n_clicks')]
)
def test_callback(n_clicks):
    """Very simple test callback"""
    if n_clicks:
        return f"Button clicked {n_clicks} times!"
    return "Click the button!"

# Add callback to handle booking confirmation
@app.callback(
    Output('teacher-name', 'value'),
    Output('class-subject', 'value'),
    Output('booking-notes', 'value'),
    Input('confirm-booking', 'n_clicks'),
    State('teacher-name', 'value'),
    State('class-subject', 'value'),
    State('booking-notes', 'value'),
    State('booking-data', 'children')
)
def handle_booking_confirmation(n_clicks, teacher_name, class_subject, notes, booking_data):
    """Handle booking confirmation"""
    if n_clicks and booking_data:
        try:
            booking_info = json.loads(booking_data)
            # Here you would save the booking to a database
            print(f"Booking confirmed: {teacher_name} - {class_subject} - {booking_info}")
            
            # Clear the form
            return "", "", ""
        except:
            pass
    
    return teacher_name, class_subject, notes

print("Callbacks defined successfully!")

# Function to integrate with Google Sheets
def setup_google_sheets_integration():
    """Set up Google Sheets integration"""
    global sample_schedule_data
    
    try:
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # You'll need to provide your credentials file path
        credentials_file = 'your-credentials.json'  # Replace with your actual file path
        sheet_name = 'Your Sheet Name'  # Replace with your actual sheet name
        
        if os.path.exists(credentials_file):
            creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
            client = gspread.authorize(creds)
            
            # Open your Google Sheet by title
            sheet = client.open(sheet_name).sheet1
            
            # Get all values
            data = sheet.get_all_records()
            
            # Convert to the format expected by the calendar
            for row in data:
                if 'Date' in row and 'Day Type' in row:
                    date_str = row['Date']
                    day_type = row['Day Type']
                    notes = row.get('Notes', '')
                    
                    # Convert date format if needed
                    try:
                        # Assuming date is in MM/DD/YYYY format
                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                        date_key = date_obj.strftime('%Y-%m-%d')
                        
                        sample_schedule_data[date_key] = {
                            'day_type': day_type,
                            'notes': notes
                        }
                    except:
                        print(f"Could not parse date: {date_str}")
            
            print(f"Successfully loaded {len(sample_schedule_data)} dates from Google Sheets!")
            
        else:
            print("Google Sheets credentials file not found.")
            print("Please provide your credentials file path and sheet name.")
            print("Current sample data will be used instead.")
            
    except Exception as e:
        print(f"Error setting up Google Sheets integration: {e}")
        print("Using sample data instead.")

# Uncomment and modify the following lines with your actual credentials:
# setup_google_sheets_integration()

if __name__ == '__main__':
    print("Starting the School Library Calendar...")
    print("The calendar will be available at: http://127.0.0.1:8050")
    print("Press Ctrl+C to stop the server")
    app.run(debug=True, host='127.0.0.1', port=8050) 