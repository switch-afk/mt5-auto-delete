from flask import Flask, render_template, request, redirect, url_for, session
import pandas as pd
import math
import json
import os
import shutil
from io import BytesIO
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key

# Store data in a simple global variable (resets on server restart)
trade_data_store = {
    'all_trades': [],
    'filtered_trades': [],
    'trader_info': {}
}

@app.route('/')
def home():
    # Get data from global store with pagination
    trader_info = trade_data_store['trader_info']
    
    # Use filtered trades if available, otherwise show all trades
    if session.get('filter_type') and 'filtered_trades' in trade_data_store and trade_data_store['filtered_trades']:
        trades_to_display = trade_data_store['filtered_trades']
    else:
        # Show all trades by default
        trades_to_display = trade_data_store['all_trades']
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Calculate pagination
    total = len(trades_to_display)
    start = (page - 1) * per_page
    end = start + per_page
    trades_page = trades_to_display[start:end] if trades_to_display else []
    
    # Calculate pagination info
    total_pages = math.ceil(total / per_page) if total > 0 else 1
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('index.html', 
                         title='Terminal | Trade Analyzer',
                         message='Trade Analyzer Ready',
                         trades=trades_page,
                         trader_info=trader_info,
                         filtered_trades_count=session.get('filtered_trades_count'),
                         pagination={
                             'page': page,
                             'total_pages': total_pages,
                             'has_prev': has_prev,
                             'has_next': has_next,
                             'total_trades': total
                         })

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(url_for('home'))
    
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('home'))
    
    if file and file.filename.endswith('.xlsx'):
        try:
            # Read Excel file
            file_content = BytesIO(file.read())
            
            # Suppress openpyxl warnings
            import warnings
            warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')
            
            # Read the Excel file without header first to get raw data
            df_raw = pd.read_excel(file_content, engine='openpyxl', header=None)
            
            # Extract trader info from specific rows based on the structure we found
            trader_info = {}
            
            # Row 2 (index 1): Name is in column 4 (index 3)
            if len(df_raw) > 1 and len(df_raw.columns) > 3:
                name_value = df_raw.iloc[1, 3]  # Row 2, Column 4
                if pd.notna(name_value):
                    trader_info['name'] = str(name_value).strip()
            
            # Row 3 (index 2): Account is in column 4 (index 3)  
            if len(df_raw) > 2 and len(df_raw.columns) > 3:
                account_value = df_raw.iloc[2, 3]  # Row 3, Column 4
                if pd.notna(account_value):
                    trader_info['account'] = str(account_value).strip()
            
            # Reset file pointer for second read
            file_content.seek(0)
            
            # Read the data starting from row 7 (index 6) which has the headers
            df_trades = pd.read_excel(file_content, engine='openpyxl', header=6)
            
            all_trades = []
            
            # The profit column should be the last column (index 12, which is "Profit")
            profit_col = 'Profit'
            position_col = 'Position'
            time_col = 'Time'
            
            # Check if columns exist and process all trades
            if profit_col in df_trades.columns:
                for index, row in df_trades.iterrows():
                    try:
                        profit = pd.to_numeric(row[profit_col], errors='coerce')
                        if pd.notna(profit):  # Process all trades with valid profit values
                            position = row[position_col] if position_col in df_trades.columns else 'N/A'
                            time = row[time_col] if time_col in df_trades.columns else 'N/A'
                            
                            # Clean up the data
                            position_str = str(position) if pd.notna(position) else 'N/A'
                            time_str = str(time) if pd.notna(time) else 'N/A'
                            
                            # Determine trade type
                            if profit > 0:
                                trade_type = 'PROFIT'
                            elif profit < 0:
                                trade_type = 'LOSS'
                            else:
                                trade_type = 'BREAKEVEN'
                            
                            all_trades.append({
                                'position': position_str,
                                'time': time_str,
                                'profit': float(profit),
                                'type': trade_type,
                                'original_index': index  # Store original index for consecutive detection
                            })
                    except (ValueError, TypeError):
                        continue
            
            # Store data in global store (no session size limits)
            trade_data_store['all_trades'] = all_trades
            trade_data_store['trader_info'] = trader_info
            
            # Clear any existing filters when new data is uploaded
            session.pop('trade_type', None)
            session.pop('filter_type', None)
            session.pop('filtered_trades_count', None)
            trade_data_store['filtered_trades'] = []
            
            if not all_trades:
                session['error'] = "No trades found in the uploaded file"
            else:
                session.pop('error', None)  # Clear any previous errors
            
        except Exception as e:
            # Handle Excel parsing errors
            session['error'] = f"Error parsing Excel file: {str(e)}"
    else:
        session['error'] = "Please upload a valid XLSX file"
    
    return redirect(url_for('home'))

@app.route('/filter_trades', methods=['POST'])
def filter_trades():
    trade_type = request.form.get('trade_type', 'all')
    filter_type = request.form.get('filter_type', 'all')
    
    session['trade_type'] = trade_type
    session['filter_type'] = filter_type
    
    # Get all trades from storage
    all_trades = trade_data_store['all_trades']
    
    # First filter by trade type (profit/loss/all)
    if trade_type == 'profit':
        trades = [trade for trade in all_trades if trade['profit'] > 0]
    elif trade_type == 'loss':
        trades = [trade for trade in all_trades if trade['profit'] < 0]
    else:  # 'all'
        trades = all_trades
    
    if not trades:
        session['filtered_trades_count'] = 0
        trade_data_store['filtered_trades'] = []
        return redirect(url_for('home'))
    
    # Apply consecutive filtering logic for any trade type
    if filter_type != 'all':
        filtered_trades = apply_consecutive_filter(trades, filter_type, trade_type)
    else:
        filtered_trades = trades
    
    # Store filtered results
    trade_data_store['filtered_trades'] = filtered_trades
    session['filtered_trades_count'] = len(filtered_trades)
    
    # Save position values to JSON file
    save_positions_to_json(filtered_trades)
    
    return redirect(url_for('home'))

@app.route('/clear_filter')
def clear_filter():
    session.pop('trade_type', None)
    session.pop('filter_type', None)
    session.pop('filtered_trades_count', None)
    trade_data_store['filtered_trades'] = []
    
    # Clear the JSON file when filter is cleared
    clear_positions_json()
    
    return redirect(url_for('home'))

@app.route('/clear')
def clear_data():
    trade_data_store['all_trades'] = []
    trade_data_store['filtered_trades'] = []
    trade_data_store['trader_info'] = {}
    session.pop('error', None)
    session.pop('trade_type', None)
    session.pop('filter_type', None)
    session.pop('filtered_trades_count', None)
    
    # Clear the JSON file when all data is cleared
    clear_positions_json()
    
    return redirect(url_for('home'))

@app.route('/delete_files')
def delete_files():
    """Delete all files in main/ and shots/ directories"""
    try:
        directories_to_clear = ['main', 'shots']
        deleted_files = []
        
        for directory in directories_to_clear:
            if os.path.exists(directory):
                # Get list of files before deletion for logging
                files_in_dir = os.listdir(directory)
                
                # Delete all files in the directory
                for filename in files_in_dir:
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        deleted_files.append(file_path)
                    elif os.path.isdir(file_path):
                        # Remove subdirectories and their contents
                        shutil.rmtree(file_path)
                        deleted_files.append(f"{file_path}/ (directory)")
        
        if deleted_files:
            print(f"Deleted files: {', '.join(deleted_files)}")
            session['success_message'] = f"Successfully deleted {len(deleted_files)} files/directories"
        else:
            session['success_message'] = "No files found to delete"
            
    except Exception as e:
        print(f"Error deleting files: {str(e)}")
        session['error'] = f"Error deleting files: {str(e)}"
    
    return redirect(url_for('home'))

def apply_consecutive_filter(trades, filter_type, trade_type):
    """Apply consecutive filtering logic based on filter type and trade type"""
    
    if filter_type == 'all':
        return trades
    
    # Sort trades by original index to maintain order
    sorted_trades = sorted(trades, key=lambda x: x.get('original_index', 0))
    
    # Find consecutive groups based on trade type
    consecutive_groups = find_consecutive_groups(sorted_trades, trade_type)
    
    filtered_trades = []
    
    if filter_type == 'consecutive':
        # Return only trades that are part of consecutive sequences (2+ trades)
        for group in consecutive_groups:
            if len(group) >= 2:
                filtered_trades.extend(group)
    
    elif filter_type in ['1', '2', '3', '4', '5']:
        max_count = int(filter_type)
        
        for group in consecutive_groups:
            if len(group) == 1:
                # Single trade - include if max_count >= 1
                if max_count >= 1:
                    filtered_trades.extend(group)
            else:
                # Consecutive group - take up to max_count trades
                filtered_trades.extend(group[:max_count])
    
    return filtered_trades

def find_consecutive_groups(sorted_trades, trade_type):
    """Find groups of consecutive trades of the same type"""
    if not sorted_trades:
        return []
    
    groups = []
    current_group = [sorted_trades[0]]
    
    for i in range(1, len(sorted_trades)):
        current_trade = sorted_trades[i]
        previous_trade = sorted_trades[i-1]
        
        # Check if trades are consecutive and of the same type
        if trades_are_consecutive(previous_trade, current_trade) and same_trade_type(previous_trade, current_trade, trade_type):
            current_group.append(current_trade)
        else:
            groups.append(current_group)
            current_group = [current_trade]
    
    groups.append(current_group)
    return groups

def same_trade_type(trade1, trade2, trade_type):
    """
    Check if both trades are of the same type as specified
    """
    if trade_type == 'profit':
        return trade1['profit'] > 0 and trade2['profit'] > 0
    elif trade_type == 'loss':
        return trade1['profit'] < 0 and trade2['profit'] < 0
    else:  # 'all' - for mixed consecutive trades, we look for any consecutive pattern
        return True

def save_positions_to_json(filtered_trades):
    """Save position values from filtered trades to JSON file"""
    try:
        # Extract only position values and convert to numbers (skip non-numeric)
        positions = []
        for trade in filtered_trades:
            try:
                # Try to convert position to integer/float
                position_value = trade['position']
                if position_value != 'N/A':
                    # Try to convert to number
                    numeric_position = float(position_value)
                    # If it's a whole number, convert to int
                    if numeric_position.is_integer():
                        positions.append(int(numeric_position))
                    else:
                        positions.append(numeric_position)
            except (ValueError, TypeError):
                # Skip non-numeric positions
                continue
        
        # Create main folder if it doesn't exist
        main_folder = 'main'
        if not os.path.exists(main_folder):
            os.makedirs(main_folder)
        
        # Define JSON file paths (in main folder)
        positions_file_path = os.path.join(main_folder, 'filtered_positions.json')
        count_file_path = os.path.join(main_folder, 'total_trades.json')
        
        # Delete existing files if they exist
        if os.path.exists(positions_file_path):
            os.remove(positions_file_path)
        if os.path.exists(count_file_path):
            os.remove(count_file_path)
        
        # Save positions to JSON file (only the numeric values)
        with open(positions_file_path, 'w') as json_file:
            json.dump(positions, json_file, indent=2)
        
        # Save count to separate JSON file (only the integer)
        with open(count_file_path, 'w') as json_file:
            json.dump(len(positions), json_file, indent=2)
            
        print(f"Saved {len(positions)} numeric positions to {positions_file_path}")
        print(f"Saved trade count to {count_file_path}")
        
    except Exception as e:
        print(f"Error saving positions to JSON: {str(e)}")

def clear_positions_json():
    """Clear/delete the positions JSON files"""
    try:
        main_folder = 'main'
        positions_file_path = os.path.join(main_folder, 'filtered_positions.json')
        count_file_path = os.path.join(main_folder, 'total_trades.json')
        
        if os.path.exists(positions_file_path):
            os.remove(positions_file_path)
            print(f"Cleared {positions_file_path}")
            
        if os.path.exists(count_file_path):
            os.remove(count_file_path)
            print(f"Cleared {count_file_path}")
            
    except Exception as e:
        print(f"Error clearing JSON files: {str(e)}")

def trades_are_consecutive(trade1, trade2):
    """
    Determine if two trades are consecutive based on original index.
    Two trades are consecutive if they appear one after another in the original data.
    """
    try:
        index1 = trade1.get('original_index', 0)
        index2 = trade2.get('original_index', 0)
        
        # Check if the indices are consecutive
        return index2 == index1 + 1
    except (ValueError, TypeError):
        return False

if __name__ == '__main__':
    app.run(debug=True)