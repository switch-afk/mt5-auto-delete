import pyautogui
import cv2
import numpy as np
from PIL import Image
import pytesseract
import re
import json
from datetime import datetime
import time
import os
import random

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class IntegratedOrderProcessor:
    def __init__(self):
        self.search_history = []
        self.screenshot_offset = None
        self.shots_folder = "shots"
        self.processed_orders = set()
        self.found_orders = []
        self.target_orders = []
        
        # Create shots folder if it doesn't exist
        if not os.path.exists(self.shots_folder):
            os.makedirs(self.shots_folder)
            print(f"📁 Created '{self.shots_folder}' folder for screenshots")
            
        # Configure pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.2
    
    def run_opening_script(self):
        """Execute opening.py functionality"""
        print("🚀 Running opening sequence...")
        
        # Opening coordinates from opening.py
        coordinates = [
            {"x": 946, "y": 125},
            {"x": 1651, "y": 798}, 
            {"x": 1702, "y": 153}
        ]
        
        try:
            for i, coord in enumerate(coordinates):
                print(f"  Click {i+1}: ({coord['x']}, {coord['y']})")
                pyautogui.click(coord['x'], coord['y'])
                
                if i < len(coordinates) - 1:
                    time.sleep(1)
            
            print("✅ Opening sequence completed!")
            time.sleep(2)  # Wait for interface to load
            return True
            
        except Exception as e:
            print(f"❌ Opening sequence failed: {e}")
            return False
    
    def extract_order_number_from_interface(self):
        """Extract order number using detect.py functionality"""
        print("🔍 Extracting order number from interface...")
        
        # Area coordinates from detect.py
        area_info = {
            "bounding_box": {
                "left": 626,
                "top": 135,
                "width": 290,
                "height": 92
            }
        }
        
        bbox = area_info['bounding_box']
        
        try:
            # Take screenshot of the defined area
            screenshot = pyautogui.screenshot(region=(
                bbox['left'], 
                bbox['top'], 
                bbox['width'], 
                bbox['height']
            ))
            
            # Convert to numpy array for preprocessing
            img_array = np.array(screenshot)
            
            # Preprocess image for better OCR
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            kernel = np.ones((1,1), np.uint8)
            denoised = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Scale up image for better OCR
            scaled = cv2.resize(denoised, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(scaled)
            
            # Try multiple OCR configurations
            configs = [
                '--psm 6 -c tessedit_char_whitelist=0123456789#',
                '--psm 7 -c tessedit_char_whitelist=0123456789#',
                '--psm 8 -c tessedit_char_whitelist=0123456789#',
                '--psm 6'
            ]
            
            best_number = None
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_image, config=config)
                    print(f"  OCR text: '{text.strip()}'")
                    
                    # Updated patterns to handle # at start and space at end
                    patterns = [
                        r'#\s*(\d{7,12})\s',      # # followed by 8-10 digits followed by space
                        r'#\s*(\d{7,12})$',       # # followed by 8-10 digits at end of line
                        r'#\s*(\d{7,12})',        # # followed by 8-10 digits (fallback)
                        r'Order[e\-]*\s*#?\s*(\d{7,12})\s',  # Order followed by optional # and 8-10 digits and space
                        r'Orde[e\-]*\s*#?\s*(\d{7,12})\s',   # Handle OCR mistakes with space
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            candidate = matches[0]
                            if 8 <= len(candidate) <= 10:
                                best_number = candidate
                                print(f"  Found order number: {candidate}")
                                break
                    
                    if best_number:
                        break
                        
                except Exception as e:
                    continue
            
            # Fallback: Look for 8-10 digit numbers that might be after # and before space
            if not best_number:
                for config in ['--psm 6']:
                    try:
                        text = pytesseract.image_to_string(processed_image, config=config)
                        # Look for pattern: # followed by digits followed by space or end
                        fallback_patterns = [
                            r'#\s*(\d{7,12})\s',
                            r'#\s*(\d{7,12})$',
                            r'#(\d{7,12})\s',
                            r'(\d{7,12})\s'  # Just digits followed by space as last resort
                        ]
                        
                        for pattern in fallback_patterns:
                            numbers = re.findall(pattern, text)
                            if numbers:
                                best_number = numbers[0]
                                print(f"  Found fallback number: {best_number}")
                                break
                        
                        if best_number:
                            break
                    except:
                        continue
            
            if best_number:
                print(f"✅ Extracted order number: {best_number}")
                return best_number
            else:
                print("❌ Could not extract order number")
                return None
                
        except Exception as e:
            print(f"❌ Order extraction failed: {e}")
            return None
    
    def run_delete_sequence(self):
        """Execute delete.py functionality"""
        print("🗑️ Running delete sequence...")
        
        # Delete coordinates from delete.py
        coordinates = [
            {"x": 964, "y": 281},
            {"x": 1331, "y": 832}
        ]
        
        try:
            # Step 1: Click on first coordinate
            print(f"  1. Clicking at ({coordinates[0]['x']}, {coordinates[0]['y']})")
            pyautogui.click(coordinates[0]['x'], coordinates[0]['y'])
            time.sleep(5)
            
            # Step 2: Ctrl + A (Select All)
            print("  2. Pressing Ctrl+A (Select All)")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            # Step 3: Delete
            print("  3. Pressing Delete")
            pyautogui.press('delete')
            time.sleep(0.2)
            
            # Step 4: Tab
            print("  4. Pressing Tab")
            pyautogui.press('tab')
            time.sleep(0.2)
            
            # Step 5: Enter
            print("  5. Pressing Enter")
            pyautogui.press('enter')
            time.sleep(0.3)
            
            # Step 6: Click on second coordinate
            print(f"  6. Clicking at ({coordinates[1]['x']}, {coordinates[1]['y']})")
            pyautogui.click(coordinates[1]['x'], coordinates[1]['y'])
            time.sleep(0.3)
            
            # Step 7: Tab (after second click)
            print("  7. Pressing Tab (after second click)")
            pyautogui.press('tab')
            time.sleep(0.2)
            
            # Step 8: Enter (after second click)
            print("  8. Pressing Enter (after second click)")
            pyautogui.press('enter')
            time.sleep(0.3)
            
            # Step 9: Move mouse randomly
            print("  9. Moving mouse slightly...")
            current_x, current_y = pyautogui.position()
            
            offset_x = random.randint(-50, 50)
            offset_y = random.randint(-50, 50)
            
            new_x = max(50, min(current_x + offset_x, pyautogui.size()[0] - 50))
            new_y = max(50, min(current_y + offset_y, pyautogui.size()[1] - 50))
            
            pyautogui.moveTo(new_x, new_y, duration=0.5)
            
            print("✅ Delete sequence completed!")
            time.sleep(1)  # Wait for deletion to process
            return True
            
        except Exception as e:
            print(f"❌ Delete sequence failed: {e}")
            return False
    
    def load_orders_from_json(self):
        """Load order numbers from JSON files in main folder"""
        orders = set()
        
        # Load from main/filtered_positions.json
        try:
            with open('main/filtered_positions.json', 'r') as f:
                filtered_data = json.load(f)
                print(f"📄 Loaded main/filtered_positions.json")
                
                if isinstance(filtered_data, list):
                    for item in filtered_data:
                        order_str = str(item).strip()
                        if order_str.isdigit():
                            orders.add(order_str)
                            
                print(f"  Found {len(filtered_data)} orders in filtered_positions.json")
                            
        except FileNotFoundError:
            print("⚠️ main/filtered_positions.json not found")
        except Exception as e:
            print(f"❌ Error loading main/filtered_positions.json: {e}")
        
        # Load from main/total_trades.json
        try:
            with open('main/total_trades.json', 'r') as f:
                trades_data = json.load(f)
                print(f"📄 Loaded main/total_trades.json")
                
                if isinstance(trades_data, list):
                    for item in trades_data:
                        order_str = str(item).strip()
                        if order_str.isdigit():
                            orders.add(order_str)
                            
                print(f"  Found {len(trades_data)} orders in total_trades.json")
                            
        except FileNotFoundError:
            print("⚠️ main/total_trades.json not found")
        except Exception as e:
            print(f"❌ Error loading main/total_trades.json: {e}")
        
        orders_list = sorted(list(orders))
        print(f"📊 Total unique orders loaded: {len(orders_list)}")
        
        if orders_list:
            print(f"📋 Sample orders: {orders_list[:5]}...")
            if len(orders_list) > 5:
                print(f"    ... and {len(orders_list) - 5} more")
        
        return orders_list
    
    def click_and_screenshot(self):
        """Click at saved coordinates and take screenshot"""
        click_coords = (641, 759)
        screenshot_points = [(629, 171), (716, 172), (627, 820), (774, 816)]
        
        pyautogui.click(click_coords[0], click_coords[1])
        print(f"Clicked at ({click_coords[0]}, {click_coords[1]})")
        pyautogui.sleep(1)
        
        x_coords = [p[0] for p in screenshot_points]
        y_coords = [p[1] for p in screenshot_points]
        
        left = min(x_coords)
        top = min(y_coords)
        right = max(x_coords)
        bottom = max(y_coords)
        
        width = right - left
        height = bottom - top
        
        screenshot = pyautogui.screenshot(region=(left, top, width, height))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"integrated_orders_{timestamp}.png"
        
        filepath = os.path.join(self.shots_folder, filename)
        screenshot.save(filepath)
        print(f"Screenshot saved: {filepath}")
        
        self.screenshot_offset = (left, top)
        return screenshot, filepath
    
    def extract_all_orders(self, screenshot):
        """Extract all order IDs from screenshot including selected orders"""
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Standard OCR
        scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(scaled)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        text = pytesseract.image_to_string(thresh, config=custom_config)
        
        orders = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and len(re.findall(r'\d', line)) >= 8:
                order_matches = re.findall(r'\d{8,}', line)
                for order in order_matches:
                    if order not in orders:
                        orders.append(order)
        
        # Blue order detection
        selected_orders = self.extract_selected_orders(img)
        for selected_order in selected_orders:
            if selected_order not in orders:
                orders.append(selected_order)
        
        return orders
    
    def extract_selected_orders(self, img):
        """Extract orders from blue highlighted/selected rows"""
        selected_orders = []
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([140, 255, 255])
        blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        contours, _ = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            if w < 50 or h < 15:
                continue
            
            blue_region = img[y:y+h, x:x+w]
            gray_region = cv2.cvtColor(blue_region, cv2.COLOR_BGR2GRAY)
            inverted = cv2.bitwise_not(gray_region)
            scaled_inverted = cv2.resize(inverted, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789'
            selected_text = pytesseract.image_to_string(scaled_inverted, config=custom_config).strip()
            
            if selected_text and len(re.findall(r'\d', selected_text)) >= 8:
                order_matches = re.findall(r'\d{8,}', selected_text)
                for order in order_matches:
                    if order not in selected_orders:
                        selected_orders.append(order)
        
        return selected_orders
    
    def find_order_location(self, screenshot, target_order_id):
        """Find the location of a specific order ID in the screenshot"""
        img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        denoised = cv2.fastNlMeansDenoising(scaled)
        _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789'
        data = pytesseract.image_to_data(thresh, config=custom_config, output_type=pytesseract.Output.DICT)
        
        found_orders = []
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            if len(text) >= 8:
                if target_order_id in text:
                    x = int(data['left'][i] / 2)
                    y = int(data['top'][i] / 2)
                    w = int(data['width'][i] / 2)
                    h = int(data['height'][i] / 2)
                    
                    screen_x = x + self.screenshot_offset[0]
                    screen_y = y + self.screenshot_offset[1]
                    
                    found_orders.append({
                        'text': text,
                        'screen_x': screen_x,
                        'screen_y': screen_y,
                        'width': w,
                        'height': h,
                        'confidence': data['conf'][i]
                    })
        
        return found_orders
    
    def double_click_order(self, order_location, click_offset_x=50):
        """Double click BESIDE the order (not on the order number)"""
        if not order_location:
            return False
        
        # Calculate click position (to the LEFT of the order text, same as before)
        click_x = order_location['screen_x'] - click_offset_x
        click_y = order_location['screen_y'] + (order_location['height'] // 2)
        
        print(f"  🖱️ Double-clicking BESIDE order at ({click_x}, {click_y}) [offset: -{click_offset_x}px]")
        pyautogui.doubleClick(click_x, click_y)
        time.sleep(2)  # Wait for order to open
        
        return True
    
    def verify_order_match(self, clicked_order, detected_order):
        """Verify if the clicked order matches the detected order"""
        if not detected_order:
            return False
        
        # Check if orders match (allow partial matches for OCR errors)
        if clicked_order == detected_order:
            print(f"✅ Perfect match: {clicked_order} = {detected_order}")
            return True
        elif clicked_order in detected_order or detected_order in clicked_order:
            print(f"✅ Partial match: {clicked_order} ≈ {detected_order}")
            return True
        else:
            print(f"❌ No match: {clicked_order} ≠ {detected_order}")
            return False
    
    def process_single_order(self, target_order, screenshot):
        """Process a single order through the complete workflow"""
        print(f"\n🎯 Processing order: {target_order}")
        print("-" * 50)
        
        # Find order location
        found_orders = self.find_order_location(screenshot, target_order)
        if not found_orders:
            print(f"❌ Order {target_order} not found in current view")
            return False
        
        best_match = max(found_orders, key=lambda x: x['confidence'])
        print(f"📍 Found order location: {best_match['text']}")
        
        # Step 1: Double-click on the order
        print("1️⃣ Double-clicking on order...")
        if not self.double_click_order(best_match):
            print("❌ Failed to double-click order")
            return False
        
        # Step 2: Extract order number from opened interface
        print("2️⃣ Extracting order number from interface...")
        detected_order = self.extract_order_number_from_interface()
        
        # Step 3: Verify match
        print("3️⃣ Verifying order match...")
        if not self.verify_order_match(target_order, detected_order):
            print(f"❌ Order mismatch - skipping deletion")
            # Close the order interface (press Escape)
            pyautogui.press('escape')
            time.sleep(1)
            return False
        
        # Step 4: Run delete sequence
        print("4️⃣ Running delete sequence...")
        if self.run_delete_sequence():
            print(f"✅ Successfully processed order: {target_order}")
            self.processed_orders.add(target_order)
            return True
        else:
            print(f"❌ Failed to delete order: {target_order}")
            return False
    
    def integrated_workflow(self):
        """Main integrated workflow"""
        print("🚀 INTEGRATED ORDER PROCESSING WORKFLOW")
        print("=" * 70)
        
        # Step 1: Run opening script
        if not self.run_opening_script():
            print("❌ Opening script failed - aborting")
            return False
        
        # Step 2: Load target orders
        self.target_orders = self.load_orders_from_json()
        if not self.target_orders:
            print("❌ No target orders loaded - aborting")
            return False
        
        print(f"\n🎯 Starting integrated processing for {len(self.target_orders)} orders...")
        
        search_attempt = 0
        previous_orders = None
        
        while True:
            search_attempt += 1
            print(f"\n🔄 Search Attempt {search_attempt}")
            
            # Check if all orders are processed
            remaining_orders = [order for order in self.target_orders if order not in self.processed_orders]
            if not remaining_orders:
                print(f"\n🎉 ALL ORDERS PROCESSED!")
                print(f"Successfully processed all {len(self.processed_orders)} orders!")
                return True
            
            # Take screenshot
            screenshot, img_filepath = self.click_and_screenshot()
            current_orders = self.extract_all_orders(screenshot)
            self.search_history.append(current_orders)
            
            print(f"📋 Current view has {len(current_orders)} orders")
            print(f"🎯 Remaining targets: {len(remaining_orders)}")
            
            # Process orders found in current view
            orders_processed_this_round = 0
            for target_order in remaining_orders:
                if any(target_order in current_order for current_order in current_orders):
                    if self.process_single_order(target_order, screenshot):
                        orders_processed_this_round += 1
                        # Take new screenshot after processing
                        screenshot, _ = self.click_and_screenshot()
                        time.sleep(1)
            
            if orders_processed_this_round > 0:
                print(f"\n📊 Processed {orders_processed_this_round} orders this round")
                continue  # Start fresh after processing orders
            
            # Check if reached top of list
            if previous_orders and set(current_orders) == set(previous_orders):
                remaining = len(self.target_orders) - len(self.processed_orders)
                print(f"\n📊 WORKFLOW COMPLETED!")
                print(f"Processed: {len(self.processed_orders)}/{len(self.target_orders)} orders")
                
                if remaining > 0:
                    print(f"❌ {remaining} orders not found:")
                    for order in remaining_orders[:10]:
                        print(f"  • {order}")
                
                return remaining == 0
            
            # Navigate up to find more orders
            print("⬆️ Navigating up to find more orders...")
            self.navigate_up_intelligently(current_orders, previous_orders)
            previous_orders = current_orders.copy()
            time.sleep(0.5)
    
    def navigate_up_intelligently(self, current_orders, previous_orders):
        """Navigate up intelligently - first select top order, then scroll"""
        
        # Calculate smart number of moves
        if not current_orders:
            moves = 15
        elif not previous_orders:
            moves = 10
        else:
            new_orders = set(current_orders) - set(previous_orders)
            if len(new_orders) == 0:
                moves = 25
            elif len(new_orders) >= len(current_orders) * 0.8:
                moves = 8
            elif len(new_orders) >= len(current_orders) * 0.5:
                moves = 12
            else:
                moves = 18
        
        print(f"📊 Order Analysis:")
        if previous_orders:
            new_orders = set(current_orders) - set(previous_orders)
            print(f"  New orders: {len(new_orders)}")
            print(f"  Old orders: {len(set(current_orders) & set(previous_orders))}")
            print(f"  Total current: {len(current_orders)}")
        
        # Step 1: First select the top order (click beside it to select)
        if current_orders:
            print(f"🎯 Selecting top order for navigation...")
            
            # Take a fresh screenshot to find top order location
            screenshot, _ = self.click_and_screenshot()
            top_order = current_orders[0]
            found_orders = self.find_order_location(screenshot, top_order)
            
            if found_orders:
                # Click BESIDE the top order using same offset as target clicking
                top_order_location = found_orders[0]
                click_x = top_order_location['screen_x'] - 50  # Same offset as double_click_order
                click_y = top_order_location['screen_y'] + (top_order_location['height'] // 2)
                
                print(f"  Clicking beside top order {top_order} at ({click_x}, {click_y}) to select it")
                pyautogui.click(click_x, click_y)
                pyautogui.sleep(0.5)
            else:
                print(f"  Could not locate top order {top_order} - using direct navigation")
        
        # Step 2: Now navigate up using arrow keys
        print(f"⬆️ Moving up {moves} positions...")
        for i in range(moves):
            pyautogui.press('up')
            if i % 5 == 4:  # Show progress every 5 moves
                print(f"  Progress: {i+1}/{moves} moves completed")
            time.sleep(0.1)
        
        print(f"✓ Completed {moves} UP movements")
        time.sleep(1)  # Wait for UI to settle
    
    def save_results(self):
        """Save processing results"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_target_orders': len(self.target_orders),
            'processed_orders': len(self.processed_orders),
            'success_rate': len(self.processed_orders) / len(self.target_orders) * 100 if self.target_orders else 0,
            'processed_order_ids': list(self.processed_orders),
            'remaining_orders': [order for order in self.target_orders if order not in self.processed_orders]
        }
        
        filename = f"integrated_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"📊 Results saved to: {filename}")

def main():
    print("🚀 Integrated Order Processing System")
    print("=" * 50)
    print("Workflow:")
    print("1. 🚀 Opening script")
    print("2. 🔍 Search and double-click orders")
    print("3. 🔍 Detect order number")
    print("4. ✅ Verify match")
    print("5. 🗑️ Delete if match")
    print("6. 🔄 Continue to next order")
    print("=" * 50)
    
    processor = IntegratedOrderProcessor()
    
    try:
        success = processor.integrated_workflow()
        processor.save_results()
        
        if success:
            print(f"\n🎉 INTEGRATED WORKFLOW COMPLETED SUCCESSFULLY!")
        else:
            print(f"\n📊 INTEGRATED WORKFLOW COMPLETED WITH SOME LIMITATIONS")
    
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Workflow cancelled by user (Ctrl+C)")
        processor.save_results()
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        processor.save_results()
    
    print(f"\n👋 Integrated processing session ended.")

if __name__ == "__main__":
    main()