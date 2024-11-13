import requests
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
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
        return quantity, card_names, set_code, collector_number
    return None


def fetch_card_image(card_name, set_code=None, collector_number=None, quality='png'):
    card_image_path = os.path.join('images', f"{card_name}.png")
    
    if not os.path.exists(card_image_path):
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


# Function to create a 3x3 PDF page with card images
def create_pdf(card_names, output_filename="mtg_proxies.pdf"):
    from reportlab.lib.units import mm

    pdf_canvas = canvas.Canvas(output_filename, pagesize=(210*mm, 297*mm))  # A4 size
    card_width, card_height = 63.5*mm, 88.9*mm  # Exact MTG card dimensions

    margin_x = (210*mm - (3 * card_width)) / 2
    margin_y = (297*mm - (3 * card_height)) / 2

    for index, card_name in enumerate(card_names):
        # Start new page and reset position counter after placing 9 cards
        if index > 0 and index % 9 == 0:
            pdf_canvas.showPage()
            
        page_index = index % 9
        x_position = margin_x + (page_index % 3) * card_width
        y_position = 297*mm - (margin_y + ((page_index // 3 + 1) * card_height))

        card_image = fetch_card_image(card_name)
        if card_image:
            image_path = os.path.join('images', f"{card_name}.png")
            card_image.save(image_path)
            pdf_canvas.drawImage(image_path, x_position, y_position, width=card_width, height=card_height)

        # "Cut lines"
        if page_index % 9 == 8 or index == len(card_names) - 1:
            # Vertical lines
            for i in range(4):
                x = margin_x + (i * card_width)
                pdf_canvas.setStrokeColor(colors.black)
                pdf_canvas.setDash(1, 2)
                pdf_canvas.line(x, 0, x, 297*mm)

            # Horizontal lines
            for i in range(4):
                y = margin_y + (i * card_height)
                pdf_canvas.line(0, y, 210*mm, y)

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
                    quantity, card_names, set_code, collector_number = parsed
                    # Add both sides of double-sided cards
                    for _ in range(quantity):
                        for card_name in card_names:
                            cards_to_print.append((card_name, set_code, collector_number))
    
    create_pdf([card[0] for card in cards_to_print])
