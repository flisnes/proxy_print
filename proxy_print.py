import requests
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from io import BytesIO
import os
import sys
import re


os.makedirs('images', exist_ok=True)

# Define where the art is located on different image qulities
# TODO: This is possible to do by formula...
ART_BOX_CONFIG = {
    'png': {
        'resolution': (745, 1040),
        'art_box': (59, 118, 687, 578)
    },
    'normal': {
        'resolution': (488, 680),
        'art_box': (35, 70, 375, 310)
    },
    'large': {
        'resolution': (672, 936),
        'art_box': (52, 105, 620, 520)
    }
}

def parse_deck_line(line):

    pattern = r'(\d+)\s+(.*?)\s+\((\w+)\)\s+(\d+)' # I think this works with the MTGA format?
    match = re.match(pattern, line.strip())
    
    if match:
        quantity = int(match.group(1))
        card_names = [name.strip() for name in match.group(2).split('//')]
        set_code = match.group(3)
        collector_number = match.group(4)
        
        # For double-faced cards, create tuple pairs of (front, back)
        if len(card_names) > 1:
            return quantity, (card_names[0], card_names[1]), set_code, collector_number
        return quantity, (card_names[0], None), set_code, collector_number
    return None


def fetch_card_image(card_name, set_code=None, collector_number=None, quality='large'):
    card_image_path = os.path.join('images', f"{card_name}.png")
    
    if os.path.exists(card_image_path):
        card_image = Image.open(card_image_path)
    else:
        if set_code and collector_number:
            url = f"https://api.scryfall.com/cards/{set_code.lower()}/{collector_number}"
        else:
            url = f"https://api.scryfall.com/cards/named?exact={card_name}"
            
        response = requests.get(url)
        if response.status_code == 200:
            card_data = response.json()
            if 'card_faces' in card_data and 'image_uris' in card_data['card_faces'][0]:
                for face in card_data['card_faces']:
                    if face['name'] == card_name:
                        image_url = face['image_uris'][quality]
                        break
            else:
                image_url = card_data['image_uris'][quality]
                
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                card_image = Image.open(BytesIO(image_response.content))
                card_image.save(card_image_path)
        else:
            print(f"Could not find card: {card_name}")
            return None

    # Test to put custom art on a card
    # TODO: Remove artist name if we replace the art?
    custom_art_path = f"{card_name}_alter.png"
    if os.path.exists(custom_art_path):
        custom_art = Image.open(custom_art_path)
        art_box = ART_BOX_CONFIG[quality]['art_box']
        custom_art = custom_art.resize((art_box[2] - art_box[0], art_box[3] - art_box[1]))
        card_image.paste(custom_art, (art_box[0], art_box[1]))
    
    return card_image


def draw_cut_lines(pdf_canvas, margin_x, margin_y, card_width, card_height):
    
    # Vertical lines
    for i in range(4):
        x = margin_x + (i * card_width)
        pdf_canvas.setStrokeColor(colors.black)
        pdf_canvas.setDash(1, 2)  # Dashed line pattern
        pdf_canvas.line(x, 0, x, 297*mm)

    # Horizontal lines
    for i in range(4):
        y = margin_y + (i * card_height)
        pdf_canvas.line(0, y, 210*mm, y)


# Function to create a 3x3 PDF page with card images
def create_pdf(cards_to_print, output_filename="mtg_proxies.pdf"):

    pdf_canvas = canvas.Canvas(output_filename, pagesize=(210*mm, 297*mm))
    card_width, card_height = 63.5*mm, 88.9*mm
    margin_x = (210*mm - (3 * card_width)) / 2
    margin_y = (297*mm - (3 * card_height)) / 2
    cards_per_page = 9

    # Check if we have any double-faced cards
    has_double_faced = any(back for _, back in cards_to_print if back is not None)
    
    # Process cards in page groups
    for page_start in range(0, len(cards_to_print), cards_per_page):
        page_cards = cards_to_print[page_start:page_start + cards_per_page]
        
        # Process front faces
        for idx, (front, _) in enumerate(page_cards):
            x_pos = margin_x + (idx % 3) * card_width
            y_pos = 297*mm - (margin_y + ((idx // 3 + 1) * card_height))
            
            card_image = fetch_card_image(front)
            if card_image:
                image_path = os.path.join('images', f"{front}.png")
                card_image.save(image_path)
                pdf_canvas.drawImage(image_path, x_pos, y_pos, width=card_width, height=card_height)
        
        # Add cut lines only on front-facing pages
        draw_cut_lines(pdf_canvas, margin_x, margin_y, card_width, card_height)
        pdf_canvas.showPage()

        # If we have double-faced cards, process backs on the next page
        if has_double_faced:
            # Add backs in mirrored positions
            for idx, (_, back) in enumerate(page_cards):
                if back:
                    # Mirror the position for proper back alignment
                    mirrored_idx = (idx // 3) * 3 + (2 - (idx % 3))
                    x_pos = margin_x + (mirrored_idx % 3) * card_width
                    y_pos = 297*mm - (margin_y + ((mirrored_idx // 3 + 1) * card_height))
                    
                    card_image = fetch_card_image(back)
                    if card_image:
                        image_path = os.path.join('images', f"{back}.png")
                        card_image.save(image_path)
                        pdf_canvas.drawImage(image_path, x_pos, y_pos, width=card_width, height=card_height)
            
            # No cut lines on back-facing pages
            pdf_canvas.showPage()

    pdf_canvas.save()
    print(f"PDF created: {output_filename}")


# Add at the bottom of the file, replacing the current cards list and create_pdf call
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python proxy-print.py <deck_file>")
        sys.exit(1)
        
    deck_file = sys.argv[1]
    cards_to_print = []
    
    with open(deck_file, 'r') as f:
        for line in f:
            if line.strip():
                parsed = parse_deck_line(line)
                if parsed:
                    quantity, card_faces, set_code, collector_number = parsed
                    # Add both sides of double-sided cards
                    for _ in range(quantity):
                        cards_to_print.append(card_faces)
    
    create_pdf(cards_to_print)
