from __future__ import annotations

import argparse
import time
import pyautogui
import pyperclip
import pandas as pd
import os
import json
import trafilatura
from tqdm import tqdm
from bs4 import BeautifulSoup
from markdownify import markdownify as md

pyautogui.FAILSAFE = True   # Move mouse to top-left corner to abort
pyautogui.PAUSE = 0.4       # Small delay between every pyautogui call

def get_coordinates_pyautogui(input_dict, filename="screen_coord.json"):
    """
    Prompts the user to position their mouse for each key in the dictionary,
    records the X/Y coordinates when they press Enter, and saves to JSON.
    """
    print("For each item, move your mouse to the desired location and press Enter.")
    print("-" * 60)
    
    for key in input_dict.keys():
        # Pause the script until the user presses Enter
        input(f"Move your mouse to the position for '{key}' and press Enter...")
        
        # Capture the current mouse coordinates
        current_x, current_y = pyautogui.position()
        
        # Update the dictionary with the new dictionary of coordinates
        input_dict[key] = {"x": current_x, "y": current_y}
        print(f"✅ Recorded '{key}' at X:{current_x}, Y:{current_y}\n")
        
    # Save the modified dictionary to a JSON file
    with open(filename, 'w') as json_file:
        json.dump(input_dict, json_file, indent=4)
        
    print(f"All coordinates successfully saved to {filename}")
    return input_dict

def click_element_at(coord:dict,mouse_move_duration=2.0,post_click_delay=0.5) -> None:
    """Click at specific screen coordinates (e.g., a button or link)."""
    x, y = coord['x'], coord['y']
    pyautogui.moveTo(x, y, duration=mouse_move_duration)
    pyautogui.click()
    time.sleep(post_click_delay)

def open_close_dev_tool_console(op_system:str):
    assert op_system in ['ios','windows','linux']
    if op_system == 'ios':
        pyautogui.hotkey("command", "option", "j")
    elif op_system == 'linux':
        pyautogui.hotkey("ctrl", "shift", "k")
    else:
        pyautogui.hotkey("ctrl", "shift", "j")

def paste_text(op_system:str):
    assert op_system in ['ios','windows','linux']
    if op_system == 'ios':
        pyautogui.hotkey("command", "v")
    elif op_system == 'linux':
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.hotkey("ctrl", "v")

def screen_coord_validator(coords:dict) -> bool:
    error_msgs = []
    carts = ['x','y']
    keys = ['browser_logo','browser_close','search_bar','dev_tool_console']
    for k in keys:
        if not k in coords:
            error_msgs.append('Coordinate '+k+' is missing')
    for k in keys:
        if k in coords:
            if isinstance(coords[k],dict):
                for c in carts:
                    if not c in coords[k]:
                        error_msgs.append('Key '+c+' is missing in coordinate '+k)
                    else:
                        if (not isinstance(coords[k][c],int)) or (int(coords[k][c]) < 0):
                            error_msgs.append('Cartesian component '+c+' in coordinate '+k+' must be a non-negative integer number. Current value: '+str(coords[k][c]))
            else:
                error_msgs.append('Coordinate '+k+' must be a dicitonary with two keys: "x" and "y"')

    if len(error_msgs) > 0:
        print('ERRORS FOUND IN SCREEN-COORDINATES FILE:')
        for e in error_msgs:
            print('>> '+e)

    return len(error_msgs) == 0

def main(screen_coord_file:str, land_pages_fname:str, op_system:str) -> None:
    '''
    DESCRIPTION

    INPUT

    screen_coord_file: JSON file containing the screen coordinates
    needed to open/close the browser and click on the search bar and
    inspection dev tool console.

    land_pages_fname: Excel file (produced by the prepare_raw_data.ipynb
    script) that contains EWOQ evals landing page.

    '''

    # Check for valid input
    assert os.path.isfile(screen_coord_file) and screen_coord_file.endswith('.json')
    assert os.path.isfile(land_pages_fname) and land_pages_fname.endswith('.xlsx')
    assert op_system in ['ios','windows','linux']
    
    # Load screen coordinates
    screen_coords = None
    with open(screen_coord_file, 'r', encoding='utf-8') as file:
        screen_coords = json.load(file)

    # Verify that screen coordinates are complete and valid
    assert screen_coord_validator(screen_coords)

    # Load landing pages
    df = pd.read_excel(land_pages_fname,sheet_name='Sheet1')
    df = df[df['Ad Type'].isin(['shopping','text'])]

    # Open browser
    print('>> Scrapping landing page content')
    click_element_at(screen_coords['browser_logo'])
    time.sleep(5.0)

    # Iterate over evals
    data = {'LP content':[],'LP scrapping succeeded':[],'LP scrapping error status':[]}
    for i in tqdm(range(len(df))):
        # Copy landing page URL
        lp_url = str(df['land_page'].iloc[i])
        pyperclip.copy(lp_url)

        # Search URL in search bar
        click_element_at(screen_coords['search_bar'],mouse_move_duration=0.5) # click at search bar
        paste_text(op_system)
        pyautogui.press("enter")
        time.sleep(15.0)

        # Open devtool console
        open_close_dev_tool_console(op_system)
        time.sleep(0.5)

        # Click at dev tool console to ensure copy-command is typed in it
        click_element_at(screen_coords['dev_tool_console'],mouse_move_duration=0.5)

        # Copy rendered HTML
        pyautogui.typewrite('copy(document.documentElement.outerHTML)', interval=0.03)
        pyautogui.press("enter")
        time.sleep(0.5)
        rend_html = pyperclip.paste()

        # lp_content_markdown = trafilatura.extract(rend_html,output_format="markdown",include_links=True,include_tables=True,include_images=False)
        soup = BeautifulSoup(rend_html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg", "iframe", "nav", "footer", "form"]):
            tag.decompose()
        lp_content_markdown = md(str(soup), heading_style="ATX", strip=["img"])

        # Close devtool console
        open_close_dev_tool_console(op_system)
        time.sleep(0.5)

        data['LP content'].append(lp_content_markdown)
        data['LP scrapping succeeded'].append('True')
        data['LP scrapping error status'].append('')

    # Close browser
    click_element_at(screen_coords['browser_close'])
    print('>> Done')

    # Save landing-page-extended spreadsheet
    fname = 'AQR_data_with_LP_content.xlsx'
    ext_df = pd.concat([df, pd.DataFrame(data)], axis=1)
    ext_df.to_excel(fname,index=False,engine_kwargs={"options": {"strings_to_urls": False}})
    print('>> Saved landing page content in '+fname)

if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser(description="A script that scrapes landing pages content for LLM consumption.")
    parser.add_argument("screen_coord_file", type=str, help="Path to the JSON file containing screen coordinates.")
    parser.add_argument('-s', '--sample', action='store_true', help="Enable coordinates sampling mode")
    parser.add_argument("-ef", "--excel_file", default="None", help="Excel file produced by prepare_raw_data.ipynb script.")
    parser.add_argument("-os", "--operating_system", default="None", help="Operating system in which this script will be executed: < ios | linux | windows >.")
    args = parser.parse_args()

    # Sample screen coordinates
    if args.sample:
        screen_coords = None
        with open(args.screen_coord_file, 'r', encoding='utf-8') as file:
            screen_coords = json.load(file)
        get_coordinates_pyautogui(screen_coords,args.screen_coord_file)
    # Scrap landing pages content
    else:
        main(args.screen_coord_file,args.excel_file,args.operating_system)